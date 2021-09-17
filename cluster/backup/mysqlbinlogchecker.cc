/*
   Copyright (c) 2000, 2020, Oracle and/or its affiliates.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License, version 2.0,
   as published by the Free Software Foundation.

   This program is also distributed with certain software (including
   but not limited to OpenSSL) that is licensed under separate terms,
   as designated in a particular file or component or in included license
   documentation.  The authors of MySQL hereby grant you an additional
   permission to link the program and your derivative works with the
   separately licensed software that they have included with MySQL.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License, version 2.0, for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA
*/

/*
   Standalone program to read a MySQL binary log (or relay log).

   Should be able to read any file of these categories, even with
   --start-position.
   An important fact: the Format_desc event of the log is at most the 3rd event
   of the log; if it is the 3rd then there is this combination:
   Format_desc_of_slave, Rotate_of_master, Format_desc_of_master.
*/

#include "client/mysqlbinlog.h"

#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <algorithm>
#include <map>
#include <utility>

#include <iostream>
#include <fstream>

#include "caching_sha2_passwordopt-vars.h"
#include "client/client_priv.h"
#include "compression.h"
#include "libbinlogevents/include/codecs/factory.h"
#include "libbinlogevents/include/compression/factory.h"
#include "libbinlogevents/include/compression/iterator.h"
#include "libbinlogevents/include/trx_boundary_parser.h"
#include "my_byteorder.h"
#include "my_dbug.h"
#include "my_default.h"
#include "my_dir.h"
#include "my_io.h"
#include "my_macros.h"
#include "my_time.h"
#include "prealloced_array.h"
#include "print_version.h"
#include "sql/binlog_reader.h"
#include "sql/log_event.h"
#include "sql/my_decimal.h"
#include "sql/rpl_constants.h"
#include "sql/rpl_gtid.h"
#include "sql_common.h"
#include "sql_string.h"
#include "sslopt-vars.h"
#include "typelib.h"
#include "welcome_copyright_notice.h"  // ORACLE_WELCOME_COPYRIGHT_NOTICE

#include <tuple>

using std::max;
using std::min;

/**
  For storing information of the Format_description_event of the currently
  active binlog. it will be changed each time a new Format_description_event is
  found in the binlog.
*/
Format_description_event glob_description_event(BINLOG_VERSION, server_version);

/**
  This class abstracts the rewriting of databases for RBR events.
 */
class Database_rewrite {
 public:
  using Rewrite_result =
      std::tuple<unsigned char *, std::size_t, std::size_t, bool>;

 private:
  class Transaction_payload_content_rewriter {
    using Rewrite_payload_result = std::tuple<unsigned char *, std::size_t,
                                              std::size_t, std::size_t, bool>;

   private:
    /**
      The event rewriter reference.
     */
    Database_rewrite &m_event_rewriter;

    /**
      Expands the buffer if needed.
    */
    std::tuple<unsigned char *, std::size_t, bool> reserve(
        unsigned char *buffer, std::size_t capacity, std::size_t size) {
      if (size > capacity) {
        auto outsize{size};
        outsize = round(((size + BINLOG_CHECKSUM_LEN) / 1024.0) + 1) * 1024;
        buffer = (unsigned char *)realloc(buffer, outsize);
        if (!buffer) {
          return std::make_tuple(nullptr, 0, true);
        }
        return std::make_tuple(buffer, outsize, false);
      } else
        return std::make_tuple(buffer, capacity, false);
    }

    class Buffer_realloc_manager {
     private:
      unsigned char **m_buffer{nullptr};

     public:
      Buffer_realloc_manager(unsigned char **buffer) : m_buffer{buffer} {}
      ~Buffer_realloc_manager() {
        if (m_buffer != nullptr) free(*m_buffer);
      }
      void release() { m_buffer = nullptr; }
    };

    Rewrite_payload_result rewrite_inner_events(
        binary_log::transaction::compression::type compression_type,
        const char *orig_payload, std::size_t orig_payload_size,
        std::size_t orig_payload_uncompressed_size,
        const binary_log::Format_description_event &fde) {
      // to return error or not
      auto err{false};
      auto error_val = Rewrite_payload_result{nullptr, 0, 0, 0, true};

      // output variables
      unsigned char *obuffer{nullptr};
      std::size_t obuffer_size{0};
      std::size_t obuffer_capacity{0};
      std::size_t obuffer_size_uncompressed{0};

      // temporary buffer for holding uncompressed and rewritten events
      unsigned char *ibuffer{nullptr};
      std::size_t ibuffer_capacity{0};

      // RAII objects
      Buffer_realloc_manager obuffer_dealloc_guard(&obuffer);
      Buffer_realloc_manager ibuffer_dealloc_guard(&ibuffer);

      // iterator to decompress events
      binary_log::transaction::compression::Iterable_buffer it(
          orig_payload, orig_payload_size, orig_payload_uncompressed_size,
          compression_type);

      // compressor to compress this again
      auto compressor =
          binary_log::transaction::compression::Factory::build_compressor(
              compression_type);

      compressor->set_buffer(obuffer, obuffer_size);
      compressor->reserve(orig_payload_uncompressed_size);
      compressor->open();

      // rewrite and compress
      for (auto ptr : it) {
        std::size_t ev_len{uint4korr(ptr + EVENT_LEN_OFFSET)};

        // reserve input buffer size (we are modifying the input buffer contents
        // before compressing it back).
        std::tie(ibuffer, ibuffer_capacity, err) =
            reserve(ibuffer, ibuffer_capacity, ev_len);
        if (err) return error_val;
        memcpy(ibuffer, ptr, ev_len);

        // rewrite the database name if needed
        std::tie(ibuffer, ibuffer_capacity, ev_len, err) =
            m_event_rewriter.rewrite_event(ibuffer, ibuffer_capacity, ev_len,
                                           fde);
        if (err) return error_val;

        auto left{ev_len};
        while (left > 0 && !err) {
          auto pos{ibuffer + (ev_len - left)};
          std::tie(left, err) = compressor->compress(pos, left);
        }

        if (err) return error_val;
        obuffer_size_uncompressed += ev_len;
      }

      compressor->close();
      std::tie(obuffer, obuffer_size, obuffer_capacity) =
          compressor->get_buffer();

      // do not dispose of the obuffer (disable RAII for obuffer)
      obuffer_dealloc_guard.release();

      // set the new one and adjust event settings
      return Rewrite_payload_result{obuffer, obuffer_capacity, obuffer_size,
                                    obuffer_size_uncompressed, false};
    }

   public:
    Transaction_payload_content_rewriter(Database_rewrite &rewriter)
        : m_event_rewriter(rewriter) {}

    /**
      This member function SHALL decompress, rewrite the contents of the
      payload event, compress it again and then re-encode it.

      @param buffer the buffer holding this event encoded.
      @param buffer_capacity the capacity of the buffer.
      @param fde The format description event to decode this event.

      @return a tuple with the result of the rewrite.
     */
    Rewrite_result rewrite_transaction_payload(
        unsigned char *buffer, std::size_t buffer_capacity,
        binary_log::Format_description_event const &fde) {
      DBUG_ASSERT(buffer[EVENT_TYPE_OFFSET] ==
                  binary_log::TRANSACTION_PAYLOAD_EVENT);
      binary_log::Transaction_payload_event tpe((const char *)buffer, &fde);

      auto orig_payload{tpe.get_payload()};
      auto orig_payload_size{tpe.get_payload_size()};
      auto orig_payload_uncompressed_size{tpe.get_uncompressed_size()};
      auto orig_payload_compression_type{tpe.get_compression_type()};

      unsigned char *rewritten_payload{nullptr};
      std::size_t rewritten_payload_size{0};
      std::size_t rewritten_payload_capacity{0};
      std::size_t rewritten_payload_uncompressed_size{0};

      auto rewrite_payload_res{false};
      auto has_crc{fde.footer()->checksum_alg ==
                   binary_log::BINLOG_CHECKSUM_ALG_CRC32};

      // Rewrite its contents as needed
      std::tie(rewritten_payload, rewritten_payload_capacity,
               rewritten_payload_size, rewritten_payload_uncompressed_size,
               rewrite_payload_res) =
          rewrite_inner_events(orig_payload_compression_type, orig_payload,
                               orig_payload_size,
                               orig_payload_uncompressed_size, fde);

      if (rewrite_payload_res) return Rewrite_result{nullptr, 0, 0, true};

      // create a new TPE with the new buffer
      binary_log::Transaction_payload_event new_tpe(
          reinterpret_cast<const char *>(rewritten_payload),
          rewritten_payload_size, orig_payload_compression_type,
          rewritten_payload_uncompressed_size);

      // start encoding it
      auto codec =
          binary_log::codecs::Factory::build_codec(tpe.header()->type_code);
      uchar tpe_buffer[binary_log::Transaction_payload_event::MAX_DATA_LENGTH];
      auto result = codec->encode(new_tpe, tpe_buffer, sizeof(tpe_buffer));
      if (result.second == true) return Rewrite_result{nullptr, 0, 0, true};

      // Now adjust the event buffer itself
      auto new_data_size = result.first + rewritten_payload_size;
      auto new_event_size = LOG_EVENT_HEADER_LEN + new_data_size;
      if (has_crc) new_event_size += BINLOG_CHECKSUM_LEN;
      if (new_event_size > buffer_capacity)
        buffer = (unsigned char *)my_realloc(PSI_NOT_INSTRUMENTED, buffer,
                                             new_event_size, MYF(0));

      // now write everything into the event buffer
      auto ptr = buffer;

      // preserve the current event header, but adjust the event size
      int4store(ptr + EVENT_LEN_OFFSET, new_event_size);
      ptr += LOG_EVENT_HEADER_LEN;

      // add the new tpe header
      memmove(ptr, tpe_buffer, result.first);
      ptr += result.first;

      // add the new payload
      memmove(ptr, rewritten_payload, rewritten_payload_size);
      ptr += rewritten_payload_size;

      // now can free the new payload, as we have moved it to the
      // event buffer
      free(rewritten_payload);

      // recalculate checksum
      if (has_crc) {
        ha_checksum crc{0};
        uchar buf[BINLOG_CHECKSUM_LEN];
        crc = checksum_crc32(crc, buffer, new_event_size - BINLOG_CHECKSUM_LEN);
        int4store(buf, crc);
        memcpy(ptr, buf, sizeof(buf));
      }

      return Rewrite_result{buffer, new_event_size, new_event_size, false};
    }
  };

 protected:
  /**
    A map that establishes the relationship between from the source
    database name that is to be rewritten into the target one.

    The key of the map is the "from" database name. The value of the
    map is is the "to" database name that we are rewritting the
    name into.
   */
  std::map<std::string, std::string> m_dict;

  /**
    A special rewriter for those transactions that are enclosed in a
    Transaction_payload event.
   */
  std::unique_ptr<Transaction_payload_content_rewriter>
      m_transaction_payload_rewriter{nullptr};

  /**
    This function gets the offset in the buffer for the dbname and
    dbname length.

    @param buffer the event buffer
    @param buffer_size the event length
    @param fde the format description event to decode parts of this buffer

    @return a tuple containing:
            - dbname offset
            - dbname length offset
            - boolean specifying whether this is an event that needs rewrite
              checks
            - boolean specifying whether an error was found
  */
  std::tuple<my_off_t, my_off_t, bool, bool> get_dbname_and_dblen_offsets(
      const unsigned char *buffer, size_t buffer_size,
      binary_log::Format_description_event const &fde) {
    my_off_t off_dbname = 0;
    my_off_t off_dbname_len = 0;
    bool error = false;
    bool needs_rewrite_check = false;
    auto event_type = (Log_event_type)buffer[EVENT_TYPE_OFFSET];

    switch (event_type) {
      case binary_log::TABLE_MAP_EVENT: {
        /*
          Before rewriting:

          +-------------+-----------+----------+------+----------------+
          |common_header|post_header|old_db_len|old_db|event data...   |
          +-------------+-----------+----------+------+----------------+

          Note that table map log event uses only one byte for database length.

        */
        off_dbname_len = fde.common_header_len +
                         fde.post_header_len[binary_log::TABLE_MAP_EVENT - 1];
        off_dbname = off_dbname_len + 1;
        needs_rewrite_check = true;
      } break;
      case binary_log::EXECUTE_LOAD_QUERY_EVENT:
      case binary_log::QUERY_EVENT: {
        /*
          The QUERY_EVENT buffer structure:

          Before Rewriting :

            +-------------+-----------+-----------+------+------+
            |common_header|post_header|status_vars|old_db|...   |
            +-------------+-----------+-----------+------+------+

          After Rewriting :

            +-------------+-----------+-----------+------+------+
            |common_header|post_header|status_vars|new_db|...   |
            +-------------+-----------+-----------+------+------+

          The db_len is inside the post header, more specifically:

            +---------+---------+------+--------+--------+------+
            |thread_id|exec_time|db_len|err_code|status_vars_len|
            +---------+---------+------+--------+--------+------+

          Thence we need to change the post header and the payload,
          which is the one carrying the database name.

          In case the new database name is longer than the old database
          length, it will reallocate the buffer.
        */
        uint8 common_header_len = fde.common_header_len;
        uint8 query_header_len =
            fde.post_header_len[binary_log::QUERY_EVENT - 1];
        const unsigned char *ptr = buffer;
        uint sv_len = 0;

        DBUG_EXECUTE_IF("simulate_corrupt_event_len", buffer_size = 0;);
        /* Error if the event content is too small */
        if (buffer_size < (common_header_len + query_header_len)) {
          error = true;
          goto end;
        }

        /* Check if there are status variables in the event */
        if ((query_header_len -
             binary_log::Query_event::QUERY_HEADER_MINIMAL_LEN) > 0) {
          sv_len = uint2korr(ptr + common_header_len +
                             binary_log::Query_event::Q_STATUS_VARS_LEN_OFFSET);
        }

        /* now we have a pointer to the position where the database is. */
        off_dbname_len =
            common_header_len + binary_log::Query_event::Q_DB_LEN_OFFSET;
        off_dbname = common_header_len + query_header_len + sv_len;

        if (off_dbname_len > buffer_size || off_dbname > buffer_size) {
          error = true;
          goto end;
        }

        if (event_type == binary_log::EXECUTE_LOAD_QUERY_EVENT)
          off_dbname += Binary_log_event::EXECUTE_LOAD_QUERY_EXTRA_HEADER_LEN;
        needs_rewrite_check = true;
      } break;
      default:
        break;
    }

  end:
    return std::make_tuple(off_dbname, off_dbname_len, needs_rewrite_check,
                           error);
  }

  Rewrite_result rewrite_event(unsigned char *buffer, size_t buffer_capacity,
                               size_t data_size,
                               binary_log::Format_description_event const &fde,
                               bool recalculate_crc = false) {
    auto the_buffer{buffer};
    auto the_buffer_capacity{buffer_capacity};
    auto the_data_size{data_size};
    std::string from{};
    std::string to{};
    int64_t delta{0};
    unsigned char *dbname_ptr{nullptr};
    unsigned char *dbname_len_ptr{nullptr};

    bool error{false};
    bool needs_rewrite{false};
    size_t offset_dbname_len{0};
    size_t offset_dbname{0};
    uint8_t dbname_len{0};
    const char *dbname{nullptr};

    std::tie(offset_dbname, offset_dbname_len, needs_rewrite, error) =
        get_dbname_and_dblen_offsets(buffer, data_size, fde);
    if (error || !needs_rewrite) goto end;

    // build the "from"
    dbname_len = static_cast<uint8_t>(buffer[offset_dbname_len]);
    dbname = reinterpret_cast<const char *>(buffer + offset_dbname);
    from = std::string(dbname, dbname_len);

    // check if we need to continue
    if (!is_rewrite_needed(from)) goto end;

    // if we do, we need to find the name to rewrite to (the "to")
    to = m_dict[from];

    // need to adjust the buffer layout or even reallocate
    delta = to.size() - from.size();
    // need to reallocate
    if ((delta + data_size) > buffer_capacity) {
      the_buffer_capacity = buffer_capacity + delta;
      the_buffer = (unsigned char *)my_realloc(PSI_NOT_INSTRUMENTED, buffer,
                                               the_buffer_capacity, MYF(0));
      /* purecov: begin inspected */
      if (!the_buffer) {
        // OOM
        error = true;
        goto end;
      }
      /* purecov: end */
    }

    // adjust the size of the event
    the_data_size += delta;

    // need to move bytes around in the buffer if needed
    if (the_data_size != data_size) {
      unsigned char *to_tail_ptr = the_buffer + offset_dbname + to.size();
      unsigned char *from_tail_ptr = the_buffer + offset_dbname + from.size();
      size_t to_tail_size = data_size - (offset_dbname + from.size());

      // move the tail (so we do not risk overwriting it)
      memmove(to_tail_ptr, from_tail_ptr, to_tail_size);
    }

    dbname_ptr = the_buffer + offset_dbname;
    memcpy(dbname_ptr, to.c_str(), to.size());

    DBUG_ASSERT(to.size() < UINT8_MAX);
    dbname_len_ptr = the_buffer + offset_dbname_len;
    *dbname_len_ptr = (char)to.size();

    // Update event length in header.
    int4store(the_buffer + EVENT_LEN_OFFSET, the_data_size);

    // now recalculate the checksum
    if (recalculate_crc) {
      auto ptr = the_buffer + the_data_size - BINLOG_CHECKSUM_LEN;
      ha_checksum crc{};
      uchar buf[BINLOG_CHECKSUM_LEN];
      crc = checksum_crc32(crc, the_buffer, (ptr - the_buffer));
      int4store(buf, crc);
      memcpy(ptr, buf, sizeof(buf));
    }

  end:
    return std::make_tuple(the_buffer, the_buffer_capacity, the_data_size,
                           error);
  }

  /**
    This function shall return true if the event needs to be processed for
    rewriting the database.

    @param event_type the event type code.

    @return true if the database needs to be rewritten.
   */
  bool is_rewrite_needed_for_event(Log_event_type event_type) {
    switch (event_type) {
      case binary_log::TABLE_MAP_EVENT:
      case binary_log::EXECUTE_LOAD_QUERY_EVENT:
      case binary_log::QUERY_EVENT:
      case binary_log::TRANSACTION_PAYLOAD_EVENT:
        return true;
      default:
        return false;
    }
  }

 public:
  Database_rewrite() = default;

  ~Database_rewrite() { m_dict.clear(); }

  /**
    Shall register a rule to rewrite from one database name to another.
    @param from the database name to rewrite from.
    @param to the database name to rewrite to.
   */
  void register_rule(std::string from, std::string to) {
    m_dict.insert(std::pair<std::string, std::string>(from, to));
  }

  /**
    Shall unregister a rewrite rule for a given database. If the name is
    not registered, then no action is taken and no error reported.
    The name of database to be used in this invokation is the original
    database name.

    @param from the original database name used when the rewrite rule
                was registered.
   */
  void unregister_rule(std::string from) { m_dict.erase(from); }

  /**
    Returns true if this database name needs to be rewritten.

    @param dbname The database name.
    @return true if a database name rewrite is needed, false otherwise.
   */
  bool is_rewrite_needed(std::string dbname) {
    return !m_dict.empty() && m_dict.find(dbname) != m_dict.end();
  }

  /**
    Shall rewrite the database name in the given buffer. This function
    is called when rewriting events in raw_mode.

    @param buffer the full event still not decoded.
    @param buffer_capacity the event buffer size.
    @param data_size the size of the buffer filled with meaningful data.
    @param fde the format description event to decode the event.
    @param skip_transaction_payload_event Whether to skip the
                                          Transaction_payload_event or not

    @return a tuple containing:
            - A pointer to the buffer after the changes (if any).
            - The buffer capacity size updated.
            - The event data size.
            - A boolean specifying whether there was an error or not.
   */
  Rewrite_result rewrite_raw(unsigned char *buffer, size_t buffer_capacity,
                             size_t data_size,
                             binary_log::Format_description_event const &fde,
                             bool skip_transaction_payload_event = false) {
    DBUG_ASSERT(buffer_capacity >= data_size);
    auto event_type = (Log_event_type)buffer[EVENT_TYPE_OFFSET];
    if (m_dict.empty() || !is_rewrite_needed_for_event(event_type))
      return Rewrite_result{buffer, buffer_capacity, data_size, false};

    switch (event_type) {
      case binary_log::TRANSACTION_PAYLOAD_EVENT: {
        if (!skip_transaction_payload_event) {
          if (m_transaction_payload_rewriter == nullptr)
            m_transaction_payload_rewriter =
                std::make_unique<Transaction_payload_content_rewriter>(*this);
          return m_transaction_payload_rewriter->rewrite_transaction_payload(
              buffer, buffer_capacity, fde);
        } else
          return Rewrite_result{buffer, buffer_capacity, buffer_capacity,
                                false};
      }
      default: {
        bool recalculate_crc =
            fde.footer()->checksum_alg == binary_log::BINLOG_CHECKSUM_ALG_CRC32;
        return rewrite_event(buffer, buffer_capacity, data_size, fde,
                             recalculate_crc);
      }
    }
  }

  /**
    Rewrites the event database if needed. This function is called when
    rewriting events not in raw mode.

    @param buffer the full event still not decoded.
    @param buffer_capacity the event buffer size.
    @param data_size the size of the buffer filled with meaningful data.
    @param fde the format description event to decode the event.

    @return a tuple with the pointer to the buffer with the database rewritten,
            the rewritten buffer capacity, the rewritten buffer meaningful
            bytes, and whether there was an error or not.
   */
  Rewrite_result rewrite(unsigned char *buffer, size_t buffer_capacity,
                         size_t data_size,
                         binary_log::Format_description_event const &fde) {
    return rewrite_raw(buffer, buffer_capacity, data_size, fde, true);
  }
};

/**
  The database rewriter handler for Table map and Query log events.
 */
Database_rewrite global_database_rewriter;

/*
  The character set used should be equal to the one used in mysqld.cc for
  server rewrite-db
*/
#define mysqld_charset &my_charset_latin1

#define CLIENT_CAPABILITIES \
  (CLIENT_LONG_PASSWORD | CLIENT_LONG_FLAG | CLIENT_LOCAL_FILES)

char server_version[SERVER_VERSION_LENGTH];
ulong filter_server_id = 0;

/*
  This strucure is used to store the event and the log postion of the events
  which is later used to print the event details from correct log postions.
  The Log_event *event is used to store the pointer to the current event and
  the event_pos is used to store the current event log postion.
*/
struct buff_event_info {
  Log_event *event;
  my_off_t event_pos;
};

/*
  One statement can result in a sequence of several events: Intvar_log_events,
  User_var_log_events, and Rand_log_events, followed by one
  Query_log_event. If statements are filtered out, the filter has to be
  checked for the Query_log_event. So we have to buffer the Intvar,
  User_var, and Rand events and their corresponding log postions until we see
  the Query_log_event. This dynamic array buff_ev is used to buffer a structure
  which stores such an event and the corresponding log position.
*/
typedef Prealloced_array<buff_event_info, 16> Buff_ev;
Buff_ev *buff_ev{nullptr};

// needed by net_serv.c
ulong bytes_sent = 0L, bytes_received = 0L;
ulong mysqld_net_retry_count = 10L;
ulong open_files_limit;
ulong opt_binlog_rows_event_max_size;
uint test_flags = 0;
static FILE *result_file;

static bool opt_hexdump = false;
const char *base64_output_mode_names[] = {"NEVER", "AUTO", "UNSPEC",
                                          "DECODE-ROWS", NullS};
TYPELIB base64_output_mode_typelib = {
    array_elements(base64_output_mode_names) - 1, "", base64_output_mode_names,
    nullptr};
static enum_base64_output_mode opt_base64_output_mode = BASE64_OUTPUT_UNSPEC;
const char *remote_proto_names[] = {"BINLOG-DUMP-NON-GTIDS",
                                    "BINLOG-DUMP-GTIDS", NullS};
TYPELIB remote_proto_typelib = {array_elements(remote_proto_names) - 1, "",
                                remote_proto_names, nullptr};
static char *database = nullptr;
static char *rewrite = nullptr;
bool force_opt = false, short_form = false, idempotent_mode = false;
static bool opt_verify_binlog_checksum = true;
static char *host = nullptr;
static uint my_end_arg;

#if defined(_WIN32)
static char *shared_memory_base_name = nullptr;
#endif
static char *user = nullptr;
static char *pass = nullptr;

static uint verbose = 0;

static ulonglong start_position;
#define start_position_mot ((my_off_t)start_position)
#define stop_position_mot ((my_off_t)stop_position)

static ulonglong rec_count = 0;
static MYSQL *mysql = nullptr;
static char *dirname_for_local_load = nullptr;
ulong opt_server_id_mask = 0;
Sid_map *global_sid_map = nullptr;
Checkable_rwlock *global_sid_lock = nullptr;
Gtid_set *gtid_set_included = nullptr;
Gtid_set *gtid_set_excluded = nullptr;

static bool opt_print_table_metadata;

/**
  Exit status for functions in this file.
*/
enum Exit_status {
  /** No error occurred and execution should continue. */
  OK_CONTINUE = 0,
  /** An error occurred and execution should stop. */
  ERROR_STOP,
  /** No error occurred but execution should stop. */
  OK_STOP
};

/*
  Options that will be used to filter out events.
*/
static bool opt_skip_gtids = false;
static bool opt_require_row_format = false;

/* It is set to true when BEGIN is found, and false when the transaction ends.
 */
static bool in_transaction = false;
/* It is set to true when GTID is found, and false when the transaction ends. */
static bool seen_gtid = false;

static Exit_status check_local_log_entries(PRINT_EVENT_INFO *print_event_info,
                                          const char *logname);
static Exit_status check_single_log(PRINT_EVENT_INFO *print_event_info,
                                   const char *logname);
static Exit_status check_multiple_logs(char **argv);

struct buff_event_info buff_event;

class Load_log_processor {
  char target_dir_name[FN_REFLEN];
  size_t target_dir_name_len;

  /*
    When we see first event corresponding to some LOAD DATA statement in
    binlog, we create temporary file to store data to be loaded.
    We add name of this file to file_names set using its file_id as index.
  */
  struct File_name_record {
    char *fname;
  };

  typedef std::map<uint, File_name_record> File_names;
  File_names file_names;

  /**
    Looks for a non-existing filename by adding a numerical suffix to
    the given base name, creates the generated file, and returns the
    filename by modifying the filename argument.

    @param[in,out] filename Base filename

    @param[in,out] file_name_end Pointer to last character of
    filename.  The numerical suffix will be written to this position.
    Note that there must be a least five bytes of allocated memory
    after file_name_end.

    @retval -1 Error (can't find new filename).
    @retval >=0 Found file.
  */
  File create_unique_file(char *filename, char *file_name_end) {
    File res;
    /* If we have to try more than 1000 times, something is seriously wrong */
    for (uint version = 0; version < 1000; version++) {
      sprintf(file_name_end, "-%x", version);
      if ((res = my_create(filename, 0, O_CREAT | O_EXCL | O_WRONLY, MYF(0))) !=
          -1)
        return res;
    }
    return -1;
  }

 public:
  Load_log_processor() : file_names() {}
  ~Load_log_processor() {}

  void init_by_dir_name(const char *dir) {
    target_dir_name_len =
        (convert_dirname(target_dir_name, dir, NullS) - target_dir_name);
  }
  void init_by_cur_dir() {
    if (my_getwd(target_dir_name, sizeof(target_dir_name), MYF(MY_WME)))
      exit(1);
    target_dir_name_len = strlen(target_dir_name);
  }
  void destroy() {
    File_names::iterator iter = file_names.begin();
    File_names::iterator end = file_names.end();
    for (; iter != end; ++iter) {
      File_name_record *ptr = &iter->second;
      if (ptr->fname) {
        my_free(ptr->fname);
        memset(ptr, 0, sizeof(File_name_record));
      }
    }

    file_names.clear();
  }

  /**
    Obtain file name of temporary file for LOAD DATA statement by its
    file_id and remove it from this Load_log_processor's list of events.

    @param[in] file_id Identifier for the LOAD DATA statement.

    Checks whether we have already seen Begin_load_query event for
    this file_id. If yes, returns the file name of the corresponding
    temporary file and removes the filename from the array of active
    temporary files.  From this moment, the caller is responsible for
    freeing the memory occupied by this name.

    @return String with the name of the temporary file, or NULL if we
    have not seen any Begin_load_query_event with this file_id.
  */
  char *grab_fname(uint file_id) {
    File_name_record *ptr;
    char *res = nullptr;

    File_names::iterator it = file_names.find(file_id);
    if (it == file_names.end()) return nullptr;
    ptr = &((*it).second);
    res = ptr->fname;
    memset(ptr, 0, sizeof(File_name_record));
    return res;
  }
  Exit_status process(Begin_load_query_log_event *ce);
  Exit_status process(Append_block_log_event *ae);
  Exit_status process_first_event(const char *bname, size_t blen,
                                  const uchar *block, size_t block_len,
                                  uint file_id);
};

/**
  Process the first event in the sequence of events representing a
  LOAD DATA statement.

  Creates a temporary file to be used in LOAD DATA and writes first block of
  data to it. Registers its file name in the array of active temporary files.

  @param bname Base name for temporary file to be created.
  @param blen Base name length.
  @param block First block of data to be loaded.
  @param block_len First block length.
  @param file_id Identifies the LOAD DATA statement.
  this type of event.

  @retval ERROR_STOP An error occurred - the program should terminate.
  @retval OK_CONTINUE No error, the program should continue.
*/
Exit_status Load_log_processor::process_first_event(const char *bname,
                                                    size_t blen,
                                                    const uchar *block,
                                                    size_t block_len,
                                                    uint file_id) {
  size_t full_len = target_dir_name_len + blen + 9 + 9 + 1;
  Exit_status retval = OK_CONTINUE;
  char *fname, *ptr;
  File file;
  File_name_record rec;
  DBUG_TRACE;

  if (!(fname =
            (char *)my_malloc(PSI_NOT_INSTRUMENTED, full_len, MYF(MY_WME)))) {
    error("Out of memory.");
    return ERROR_STOP;
  }

  memcpy(fname, target_dir_name, target_dir_name_len);
  ptr = fname + target_dir_name_len;
  memcpy(ptr, bname, blen);
  ptr += blen;
  ptr += sprintf(ptr, "-%x", file_id);

  if ((file = create_unique_file(fname, ptr)) < 0) {
    error("Could not construct local filename %s%s.", target_dir_name, bname);
    my_free(fname);
    return ERROR_STOP;
  }

  rec.fname = fname;

  /*
     fname is freed in process_event()
     after Execute_load_query_log_event or Execute_load_log_event
     will have been processed, otherwise in Load_log_processor::destroy()
  */
  file_names[file_id] = rec;

  if (my_write(file, pointer_cast<const uchar *>(block), block_len,
               MYF(MY_WME | MY_NABP))) {
    error("Failed writing to file.");
    retval = ERROR_STOP;
  }
  if (my_close(file, MYF(MY_WME))) {
    error("Failed closing file.");
    retval = ERROR_STOP;
  }
  return retval;
}

/**
  Process the given Begin_load_query_log_event.

  @see Load_log_processor::process_first_event(const char*,uint,const
  char*,uint,uint)

  @param blqe Begin_load_query_log_event to process.

  @retval ERROR_STOP An error occurred - the program should terminate.
  @retval OK_CONTINUE No error, the program should continue.
*/
Exit_status Load_log_processor::process(Begin_load_query_log_event *blqe) {
  return process_first_event("SQL_LOAD_MB", 11, blqe->block, blqe->block_len,
                             blqe->file_id);
}

/**
  Process the given Append_block_log_event.

  Appends the chunk of the file contents specified by the event to the
  file created by a previous Begin_load_query_log_event.

  If the file_id for the event does not correspond to any file
  previously registered through a Begin_load_query_log_event,
  this member function will print a warning and
  return OK_CONTINUE.  It is safe to return OK_CONTINUE, because no
  query will be written for this event.  We should not print an error
  and fail, since the missing file_id could be because a (valid)
  --start-position has been specified after the Begin_load_query_log_event but
  before this Append event.

  @param ae Append_block_log_event to process.

  @retval ERROR_STOP An error occurred - the program should terminate.

  @retval OK_CONTINUE No error, the program should continue.
*/
Exit_status Load_log_processor::process(Append_block_log_event *ae) {
  DBUG_TRACE;
  File_names::iterator it = file_names.find(ae->file_id);
  const char *fname = ((it != file_names.end()) ? (*it).second.fname : nullptr);

  if (fname) {
    File file;
    Exit_status retval = OK_CONTINUE;
    if (((file = my_open(fname, O_APPEND | O_WRONLY, MYF(MY_WME))) < 0)) {
      error("Failed opening file %s", fname);
      return ERROR_STOP;
    }
    if (my_write(file, (uchar *)ae->block, ae->block_len,
                 MYF(MY_WME | MY_NABP))) {
      error("Failed writing to file %s", fname);
      retval = ERROR_STOP;
    }
    if (my_close(file, MYF(MY_WME))) {
      error("Failed closing file %s", fname);
      retval = ERROR_STOP;
    }
    return retval;
  }

  /*
    There is no Begin_load_query_log_event (a bad binlog or a big
    --start-position). Assuming it's a big --start-position, we just do
    nothing and print a warning.
  */
  warning(
      "Ignoring Append_block as there is no "
      "Begin_load_query_log_event for file_id: %u",
      ae->file_id);
  return OK_CONTINUE;
}

static Load_log_processor load_processor;

/**
  Print auxiliary statements ending a binary log (or a logical binary log
  within a sequence of relay logs; see below).

  There are two kinds of log files which can be printed by mysqlbinlog
  binlog file   - generated by mysql server when binlog is ON.
  relaylog file - generated by slave IO thread. It just stores binlog
                  replicated from master with an extra header(FD event,
                  Previous_gtid_log_event) and a tail(rotate event).
  when printing the events in relay logs, the purpose is to print
  the events generated by master, but not slave.

  There are three types of FD events:
  - Slave FD event: has F_RELAY_LOG set and end_log_pos > 0
  - Real master FD event: has F_RELAY_LOG cleared and end_log_pos > 0
  - Fake master FD event: has F_RELAY_LOG cleared and end_log_pos == 0

  (Two remarks:

  - The server_id of a slave FD event is the slave's server_id, and
    the server_id of a master FD event (real or fake) is the
    master's server_id. But this does not help to distinguish the
    types in case replicate-same-server-id is enabled.  So to
    determine the type of event we need to check the F_RELAY_LOG
    flag.

  - A fake master FD event may be generated by master's dump
    thread (then it takes the first event of the binlog and sets
    end_log_pos=0), or by the slave (then it takes the last known
    real FD event and sets end_log_pos=0.)  There is no way to
    distinguish master-generated fake master FD events from
    slave-generated fake master FD events.
  )

  There are 8 cases where we rotate a relay log:

  R1. After FLUSH [RELAY] LOGS
  R2. When mysqld receives SIGHUP
  R3. When relay log size grows too big
  R4. Immediately after START SLAVE
  R5. When slave IO thread reconnects without user doing
      START SLAVE/STOP SLAVE
  R6. When master dump thread starts a new binlog
  R7. CHANGE MASTER which deletes all relay logs
  R8. RESET SLAVE

  (Remark: CHANGE MASTER which does not delete any relay log,
  does not cause any rotation at all.)

  The 8 cases generate the three types of FD events as follows:
  - In all cases, a slave FD event is generated.
  - In cases R1 and R2, if the slave has been connected
    previously, the slave client thread that issues
    FLUSH (or the thread that handles the SIGHUP) generates a
    fake master FD event. If the slave has not been connected
    previously, there is no master FD event.
  - In case R3, the slave IO thread generates a fake master FD
    event.
  - In cases R4 and R5, if AUTOPOSITION=0 and MASTER_LOG_POS>4,
    the master dump thread generates a fake master FD event.
  - In cases R4 and R5, if AUTOPOSITION=1 or MASTER_LOG_POS<=4,
    the master dump thread generates a real master FD event.
  - In case R6, the master dump thread generates a real master FD
    event.
  - In cases R7 and R8, the slave does not generate any master FD
    event.

  We define the term 'logical binlog' as a sequence of events in
  relay logs, such that a single logical binlog may span multiple
  relay log files, and any two logical binlogs are separated by a
  real master FD event.

  A transaction's events will never be divided into two binlog files or
  two logical binlogs. But a transaction may span multiple relay logs, in which
  case a faked FD will appear in the middle of the transaction. they may be
  divided by fake master FD event and/or slave FD events.

  * Example 1

    relay-log.1
    ...
    GTID_NEXT=1
    BEGIN;

    relay-log.2
    ...
    faked Format_description_event
    INSERT ...
    COMMIT;

    For above case, it has only one logical binlog. The events
    in both relay-log.1 and relay-log.2 belong to the same logical binlog.

  * Example 2

    relay-log.1
    ...
    GTID_NEXT=1
    BEGIN;      // It is a partial transaction at the end of logical binlog

    relay-log.2
    ...
    real Format_description_event
    GTID_NEXT=1
    BEGIN;
    ...

    For above case, it has two logical binlogs. Events in relay-log.1
    and relay-log.2 belong to two different logical binlog.

  Logical binlog is handled in a similar way as a binlog file. At the end of a
  binlog file, at the end of a logical binlog or at the end of mysqlbinlog it
  should
  - rollback the last transaction if it is not complete
  - rollback the last gtid if the last event is a gtid_log_event
  - set gtid_next to AUTOMATIC

  This function is called two places:
  - Before printing a real Format_description_log_event(excluding the
    first Format_description_log_event), while mysqlbinlog is in the middle
    of printing all log files(binlog or relaylog).
  - At the end of mysqlbinlog, just after printing all log files(binlog or
    relaylog).

  @param[in,out] print_event_info Context state determining how to print.
*/
void end_binlog(PRINT_EVENT_INFO *print_event_info) {
  if (in_transaction) {
    fprintf(result_file, "ROLLBACK /* added by mysqlbinlog */ %s\n",
            print_event_info->delimiter);
  } else if (seen_gtid && !opt_skip_gtids) {
    /*
      If we are here, then we have seen only GTID_LOG_EVENT
      of a transaction and did not see even a BEGIN event
      (in_transaction flag is false). So generate BEGIN event
      also along with ROLLBACK event.
    */
    fprintf(result_file,
            "BEGIN /*added by mysqlbinlog */ %s\n"
            "ROLLBACK /* added by mysqlbinlog */ %s\n",
            print_event_info->delimiter, print_event_info->delimiter);
  }

  if (!opt_skip_gtids)
    fprintf(result_file, "%sAUTOMATIC' /* added by mysqlbinlog */ %s\n",
            Gtid_log_event::SET_STRING_PREFIX, print_event_info->delimiter);

  seen_gtid = false;
  in_transaction = false;
}

/**
  Print the given event, and either delete it or delegate the deletion
  to someone else.

  The deletion may be delegated in these cases:
  - the event is a Create_file_log_event, and is saved in load_processor.
  - the event is an Intvar, Rand or User_var event, it will be kept until
    the subsequent Query_log_event.
  - the event is a Table_map_log_event, it will be kept until the subsequent
    Rows_log_event.
  @param[in,out] print_event_info Parameters and context state
  determining how to print.
  @param[in] ev Log_event to process.
  @param[in] pos Offset from beginning of binlog file.
  @param[in] logname Name of input binlog.

  @retval ERROR_STOP An error occurred - the program should terminate.
  @retval OK_CONTINUE No error, the program should continue.
  @retval OK_STOP No error, but the end of the specified range of
  events to process has been reached and the program should terminate.
*/
static Exit_status process_event(PRINT_EVENT_INFO *print_event_info,
                                 Log_event *ev, my_off_t pos,
                                 const char *logname
                                 ) {
  Log_event_type ev_type = ev->get_type_code();
  DBUG_TRACE;
  Exit_status retval = OK_CONTINUE;

    if (!opt_hexdump)
      print_event_info->hexdump_from = 0; /* Disabled */
    else
      print_event_info->hexdump_from = pos;

    DBUG_PRINT("debug", ("event_type: %s", ev->get_type_str()));
    if (logname == NULL) {
	goto err;
    }
    // std::cout << "logname:" << logname << " event_type:" << ev->get_type_str() << std::endl;
    switch (ev_type) {
      case binary_log::PREVIOUS_GTIDS_LOG_EVENT:
	// std::cerr << "logname:" << logname << " event_type:" << ev->get_type_str() << std::endl;
	ev->print(result_file, print_event_info);
	    /* Flush head cache to result_file for every event */
             copy_event_cache_to_file_and_reinit(&print_event_info->head_cache,
                                            result_file,
                                            false /* flush result_file */);
	goto end;
      default:
	break;
    }
  goto end;

err:
  retval = ERROR_STOP;
end:
  rec_count++;
  /*
    Destroy the log_event object.
  */
  delete ev;
  return retval;
}

/**
  Auxiliary function used by error() and warning().

  Prints the given text (normally "WARNING: " or "ERROR: "), followed
  by the given vprintf-style string, followed by a newline.

  @param format Printf-style format string.
  @param args List of arguments for the format string.
  @param msg Text to print before the string.
*/
void error_or_warning(const char *format, va_list args, const char *msg) {
  fprintf(stderr, "%s: ", msg);
  vfprintf(stderr, format, args);
  fprintf(stderr, "\n");
}

/**
  Prints a message to stderr, prefixed with the text "ERROR: " and
  suffixed with a newline.

  @param format Printf-style format string, followed by printf
  varargs.
*/
void error(const char *format, ...) {
  va_list args;
  va_start(args, format);
  error_or_warning(format, args, "ERROR");
  va_end(args);
}

/**
  This function is used in log_event.cc to report errors.

  @param format Printf-style format string, followed by printf
  varargs.
*/
void sql_print_error(const char *format, ...) {
  va_list args;
  va_start(args, format);
  error_or_warning(format, args, "ERROR");
  va_end(args);
}

/**
  Prints a message to stderr, prefixed with the text "WARNING: " and
  suffixed with a newline.

  @param format Printf-style format string, followed by printf
  varargs.
*/
void warning(const char *format, ...) {
  va_list args;
  va_start(args, format);
  error_or_warning(format, args, "WARNING");
  va_end(args);
}

/**
  Frees memory for global variables in this file.
*/
static void cleanup() {
  my_free(pass);
  my_free(database);
  my_free(rewrite);
  my_free(host);
  my_free(user);
  my_free(dirname_for_local_load);

  for (size_t i = 0; i < buff_ev->size(); i++) {
    buff_event_info pop_event_array = buff_ev->at(i);
    delete (pop_event_array.event);
  }
  delete buff_ev;

  if (mysql) mysql_close(mysql);
}

static void usage() {
  printf("Usage: %s path_to_file:binlog.index\n", my_progname);
}

/**
  High-level function for dumping a named binlog.

  calls check_local_log_entries() to do the job.

  @param[in] logname Name of input binlog.

  @retval ERROR_STOP An error occurred - the program should terminate.
  @retval OK_CONTINUE No error, the program should continue.
  @retval OK_STOP No error, but the end of the specified range of
  events to process has been reached and the program should terminate.
*/
static Exit_status check_single_log(PRINT_EVENT_INFO *print_event_info,
                                   const char *logname) {
  Exit_status rc = check_local_log_entries(print_event_info, logname);
  return rc;
}

static Exit_status check_multiple_logs(char **argv) {
  DBUG_TRACE;

  PRINT_EVENT_INFO print_event_info;
  if (!print_event_info.init_ok()) return ERROR_STOP;
  /*
     Set safe delimiter, to dump things
     like CREATE PROCEDURE safely
  */
  print_event_info.verbose = short_form ? 0 : verbose;
  print_event_info.short_form = short_form;
  print_event_info.base64_output_mode = opt_base64_output_mode;
  print_event_info.skip_gtids = opt_skip_gtids;
  print_event_info.print_table_metadata = opt_print_table_metadata;
  print_event_info.require_row_format = opt_require_row_format;

  // Dump all logs.
  /*
  std::ifstream ifs (argv[1], std::ifstream::in);
  char buf[250];
  while (ifs.getline(buf, sizeof(buf))) {
	stop_position = ~(my_off_t)0;
	std::cout << buf << std::endl;
    	if ((rc = check_single_log(&print_event_info, buf)) != OK_CONTINUE)
		break;
  }
  */


  return check_single_log(&print_event_info, argv[1]);
}

 

/*
  A RAII class created to handle the memory of Log_event object
  created in the dump_remote_log_entries method.
*/
class Destroy_log_event_guard {
 public:
  Log_event **ev_del;
  Destroy_log_event_guard(Log_event **ev_arg) { ev_del = ev_arg; }
  ~Destroy_log_event_guard() {
    if (*ev_del != nullptr) delete *ev_del;
  }
};

/**
   Two things are done in this class:
   - rewrite the database name in event_data if rewrite option is configured.
   - Skip the extra BINLOG_MAGIC when reading event data if
     m_multiple_binlog_magic is set. It is used for the case when users feed
     more than one binlog files through stdin.
 */
class Mysqlbinlog_event_data_istream : public Binlog_event_data_istream {
 public:
  using Binlog_event_data_istream::Binlog_event_data_istream;

  template <class ALLOCATOR>
  bool read_event_data(unsigned char **buffer, unsigned int *length,
                       ALLOCATOR *allocator, bool verify_checksum,
                       enum_binlog_checksum_alg checksum_alg) {
    return Binlog_event_data_istream::read_event_data(
               buffer, length, allocator, verify_checksum, checksum_alg) ||
           rewrite_db(buffer, length);
  }

  void set_multi_binlog_magic() { m_multi_binlog_magic = true; }

 private:
  bool m_multi_binlog_magic = false;

  bool rewrite_db(unsigned char **buffer, unsigned int *length) {
    bool ret{false};
    size_t buffer_capacity{0};
    std::tie(*buffer, buffer_capacity, *length, ret) =
        global_database_rewriter.rewrite(*buffer, *length, *length,
                                         glob_description_event);
    if (ret) {
      error("Error applying filter while reading event");
      ret = m_error->set_type(Binlog_read_error::MEM_ALLOCATE);
      if (buffer_capacity > 0) {
        my_free(*buffer);
        *buffer = nullptr;
        *length = 0;
      }
    }
    return ret;
  }

  bool read_event_header() override {
    if (Binlog_event_data_istream::read_event_header()) return true;
    /*
      If there are more than one binlog files in the stdin, it checks and skips
      the binlog magic heads of following binlog files.
    */
    if (m_multi_binlog_magic &&
        memcmp(m_header, BINLOG_MAGIC, BINLOG_MAGIC_SIZE) == 0) {
      size_t header_len = LOG_EVENT_MINIMAL_HEADER_LEN - BINLOG_MAGIC_SIZE;

      // Remove BINLOG_MAGIC from m_header
      memmove(m_header, m_header + BINLOG_MAGIC_SIZE, header_len);
      // Read the left BINLOG_MAGIC_SIZE bytes of the header
      return read_fixed_length<Binlog_read_error::TRUNC_EVENT>(
          m_header + header_len, BINLOG_MAGIC_SIZE);
    }
    return false;
  }
};

/**
   It makes Stdin_istream support seek(only seek forward). So stdin can be used
   as a Basic_seekable_istream.
*/
class Stdin_binlog_istream : public Basic_seekable_istream,
                             public Stdin_istream {
 public:
  ssize_t read(unsigned char *buffer, size_t length) override {
    longlong ret = Stdin_istream::read(buffer, length);
    if (ret > 0) m_position += ret;
    return ret;
  }

  bool seek(my_off_t position) override {
    DBUG_ASSERT(position > m_position);
    if (Stdin_istream::skip(position - m_position)) {
      error("Failed to skip %llu bytes from stdin", position - m_position);
      return true;
    }
    m_position = position;
    return false;
  }

  /* purecov: begin inspected */
  /** Stdin has no length. It should never be called. */
  my_off_t length() override {
    DBUG_ASSERT(0);
    return 0;
  }
  /* purecov: end */

 private:
  /**
    Stores the position of the stdin stream it is reading. It is exact same to
    the count of bytes it has read.
  */
  my_off_t m_position = 0;
};

class Mysqlbinlog_ifile : public Basic_binlog_ifile {
 public:
  using Basic_binlog_ifile::Basic_binlog_ifile;

 private:
  std::unique_ptr<Basic_seekable_istream> open_file(
      const char *file_name) override {
    if (file_name && strcmp(file_name, "-") != 0) {
      IO_CACHE_istream *iocache = new IO_CACHE_istream;
      if (iocache->open(
#ifdef HAVE_PSI_INTERFACE
              PSI_NOT_INSTRUMENTED, PSI_NOT_INSTRUMENTED,
#endif
              file_name, MYF(MY_WME | MY_NABP))) {
        delete iocache;
        return nullptr;
      }
      return std::unique_ptr<Basic_seekable_istream>(iocache);
    } else {
      std::string errmsg;
      Stdin_binlog_istream *standard_in = new Stdin_binlog_istream;
      if (standard_in->open(&errmsg)) {
        error("%s", errmsg.c_str());
        delete standard_in;
        return nullptr;
      }
      return std::unique_ptr<Basic_seekable_istream>(standard_in);
    }
  }
};

typedef Basic_binlog_file_reader<
    Mysqlbinlog_ifile, Mysqlbinlog_event_data_istream,
    Binlog_event_object_istream, Default_binlog_event_allocator>
    Mysqlbinlog_file_reader;

/**
  Reads a local binlog and prints the events it sees.

  @param[in] logname Name of input binlog.

  @param[in,out] print_event_info Parameters and context state
  determining how to print.

  @retval ERROR_STOP An error occurred - the program should terminate.
  @retval OK_CONTINUE No error, the program should continue.
  @retval OK_STOP No error, but the end of the specified range of
  events to process has been reached and the program should terminate.
*/
static Exit_status check_local_log_entries(PRINT_EVENT_INFO *print_event_info,
                                          const char *logname) {
  Exit_status retval = OK_CONTINUE;

  ulong max_event_size = 0;
  mysql_get_option(nullptr, MYSQL_OPT_MAX_ALLOWED_PACKET, &max_event_size);
  Mysqlbinlog_file_reader mysqlbinlog_file_reader(opt_verify_binlog_checksum,
                                                  max_event_size);

  Format_description_log_event *fdle = nullptr;
  if (mysqlbinlog_file_reader.open(logname, start_position, &fdle)) {
    error("%s", mysqlbinlog_file_reader.get_error_str());
    return ERROR_STOP;
  }

  Transaction_boundary_parser transaction_parser(
      Transaction_boundary_parser::TRX_BOUNDARY_PARSER_APPLIER);
  transaction_parser.reset();

  if (fdle != nullptr) {
    retval = process_event(print_event_info, fdle,
                           mysqlbinlog_file_reader.event_start_pos(), logname);
    if (retval != OK_CONTINUE) return retval;
  }

  if (strcmp(logname, "-") == 0)
    mysqlbinlog_file_reader.event_data_istream()->set_multi_binlog_magic();

  for (;;) {
    char llbuff[21];
    my_off_t old_off = mysqlbinlog_file_reader.position();

    Log_event *ev = mysqlbinlog_file_reader.read_event_object();
    if (ev == nullptr) {
      /*
        if binlog wasn't closed properly ("in use" flag is set) don't complain
        about a corruption, but treat it as EOF and move to the next binlog.
      */
      if ((mysqlbinlog_file_reader.format_description_event()->header()->flags &
           LOG_EVENT_BINLOG_IN_USE_F) ||
          mysqlbinlog_file_reader.get_error_type() ==
              Binlog_read_error::READ_EOF)
        return retval;

      error(
          "Could not read entry at offset %s: "
          "Error in log format or read error 1.",
          llstr(old_off, llbuff));
      error("%s", mysqlbinlog_file_reader.get_error_str());
      return ERROR_STOP;
    }
    Log_event_type ev_type = ev->get_type_code();
    if (ev_type == binary_log::PREVIOUS_GTIDS_LOG_EVENT) {
    	retval = process_event(print_event_info, ev, old_off, logname);
	return retval;
      }
  }

  /* NOTREACHED */

  return retval;
}

/**
   GTID cleanup destroys objects and reset their pointer.
   Function is reentrant.
*/
inline void gtid_client_cleanup() {
  delete global_sid_lock;
  delete global_sid_map;
  delete gtid_set_excluded;
  delete gtid_set_included;
  global_sid_lock = nullptr;
  global_sid_map = nullptr;
  gtid_set_excluded = nullptr;
  gtid_set_included = nullptr;
}

/**
   GTID initialization.

   @return true if allocation does not succeed
           false if OK
*/
inline bool gtid_client_init() {
  bool res = (!(global_sid_lock = new Checkable_rwlock) ||
              !(global_sid_map = new Sid_map(global_sid_lock)) ||
              !(gtid_set_excluded = new Gtid_set(global_sid_map)) ||
              !(gtid_set_included = new Gtid_set(global_sid_map)));
  if (res) {
    gtid_client_cleanup();
  }
  return res;
}

int main(int argc, char **argv) {
  Exit_status retval = OK_CONTINUE;
  MY_INIT(argv[0]);

  my_init_time();  // for time functions
  tzset();         // set tzname
  /*
    A pointer of type Log_event can point to
     INTVAR
     USER_VAR
     RANDOM
    events.
  */
  buff_ev = new Buff_ev(PSI_NOT_INSTRUMENTED);

  my_getopt_use_args_separator = true;
  MEM_ROOT alloc{PSI_NOT_INSTRUMENTED, 512};
  my_getopt_use_args_separator = false;

  if (!argc) {
    usage();
    my_end(my_end_arg);
    return EXIT_FAILURE;
  }

  result_file = stdout;

  if (gtid_client_init()) {
    error("Could not initialize GTID structuress.");
    return EXIT_FAILURE;
  }

  if (opt_base64_output_mode == BASE64_OUTPUT_UNSPEC)
    opt_base64_output_mode = BASE64_OUTPUT_AUTO;

  MY_TMPDIR tmpdir;
  tmpdir.list = nullptr;
  if (!dirname_for_local_load) {
    if (init_tmpdir(&tmpdir, nullptr)) return EXIT_FAILURE;
    dirname_for_local_load =
        my_strdup(PSI_NOT_INSTRUMENTED, my_tmpdir(&tmpdir), MY_WME);
  }

  if (dirname_for_local_load)
    load_processor.init_by_dir_name(dirname_for_local_load);
  else
    load_processor.init_by_cur_dir();

  retval = check_multiple_logs(argv);

  if (tmpdir.list) free_tmpdir(&tmpdir);
  if (result_file && (result_file != stdout)) my_fclose(result_file, MYF(0));
  cleanup();

  load_processor.destroy();
  /* We cannot free DBUG, it is used in global destructors after exit(). */
  my_end(my_end_arg | MY_DONT_FREE_DBUG);
  gtid_client_cleanup();

  return (retval == ERROR_STOP ? EXIT_FAILURE : EXIT_SUCCESS);
}

#ifndef MYSQL_SERVER
void Transaction_payload_log_event::print(FILE *,
                                          PRINT_EVENT_INFO *info) const {
  DBUG_TRACE;

  bool has_crc{(glob_description_event.footer()->checksum_alg ==
                binary_log::BINLOG_CHECKSUM_ALG_CRC32)};
  Format_description_event fde_no_crc = glob_description_event;
  fde_no_crc.footer()->checksum_alg = binary_log::BINLOG_CHECKSUM_ALG_OFF;

  bool error{false};
  IO_CACHE *const head = &info->head_cache;
  size_t current_buffer_size = 1024;
  auto buffer = (uchar *)my_malloc(PSI_NOT_INSTRUMENTED, current_buffer_size,
                                   MYF(MY_WME));
  if (!info->short_form) {
    std::ostringstream oss;
    oss << "\tTransaction_Payload\t" << to_string() << std::endl;
    oss << "# Start of compressed events!" << std::endl;
    print_header(head, info, false);
    my_b_printf(head, "%s", oss.str().c_str());
  }

  // print the payload
  binary_log::transaction::compression::Iterable_buffer it(
      m_payload, m_payload_size, m_uncompressed_size, m_compression_type);

  for (auto ptr : it) {
    Log_event *ev = nullptr;
    bool is_deferred_event = false;

    // fix the checksum part
    size_t event_len = uint4korr(ptr + EVENT_LEN_OFFSET);

    // resize the buffer we are using to handle the event if needed
    if (event_len > current_buffer_size) {
      current_buffer_size =
          round(((event_len + BINLOG_CHECKSUM_LEN) / 1024.0) + 1) * 1024;
      buffer = (uchar *)my_realloc(PSI_NOT_INSTRUMENTED, buffer,
                                   current_buffer_size, MYF(0));

      /* purecov: begin inspected */
      if (!buffer) {
        // OOM
        head->error = -1;
        my_b_printf(head, "# Out of memory!");
        goto end;
      }
      /* purecov: end */
    }

    memcpy(buffer, ptr, event_len);

    // rewrite the database name if needed
    std::tie(buffer, current_buffer_size, event_len, error) =
        global_database_rewriter.rewrite(buffer, current_buffer_size, event_len,
                                         fde_no_crc);

    /* purecov: begin inspected */
    if (error) {
      head->error = -1;
      my_b_printf(head, "# Error while rewriting db for compressed events!");
      goto end;
    }
    /* purecov: end */

    // update the CRC
    if (has_crc) {
      int4store(buffer + EVENT_LEN_OFFSET, event_len + BINLOG_CHECKSUM_LEN);
      int4store(buffer + event_len, checksum_crc32(0, buffer, event_len));
      event_len += BINLOG_CHECKSUM_LEN;
    }

    // now deserialize the event
    if (binlog_event_deserialize((const unsigned char *)buffer, event_len,
                                 &glob_description_event, true, &ev)) {
      /* purecov: begin inspected */
      head->error = -1;
      my_b_printf(
          head, "# Error while handling compressed events! Corrupted binlog?");
      goto end;
      /* purecov: end */
    }

    switch (ev->get_type_code()) {
      // Statement Based Replication
      //   deferred events have to keep a copy of the buffer
      //   they are output only when the correct event comes
      //   later (Query_log_event)
      case binary_log::INTVAR_EVENT: /* purecov: inspected */
      case binary_log::RAND_EVENT:
      case binary_log::USER_VAR_EVENT:
        is_deferred_event = true; /* purecov: inspected */
        break;                    /* purecov: inspected */
      default:
        is_deferred_event = false;
        break;
    }

    ev->register_temp_buf((char *)buffer, is_deferred_event);
    ev->common_header->log_pos = header()->log_pos;

    // TODO: make this iterative, not recursive (process_event may rely
    // on global vars, and this may cause problems).
    process_event(info, ev, header()->log_pos, "");

    // lets make the buffer be allocated again, as the current
    // buffer ownership has been handed over to the defferred event
    if (is_deferred_event) {
      buffer = nullptr;        /* purecov: inspected */
      current_buffer_size = 0; /* purecov: inspected */
    }
  }

  if (!info->short_form) my_b_printf(head, "# End of compressed events!\n");

end:
  my_free(buffer);
}
#endif

void getridofunused(){
set_server_public_key(NULL, NULL);
set_get_server_public_key_option(NULL, NULL);
}
