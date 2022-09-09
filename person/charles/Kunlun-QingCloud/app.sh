sed -i "s/$1/$2/" ./app/cluster.json.mustache
echo $1:$2
rm app.tar.gz 
tar -zcf app.tar.gz app
cat ./app/cluster.json.mustache | grep $2
