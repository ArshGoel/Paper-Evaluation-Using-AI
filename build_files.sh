echo "BUILD START"
python pip install requirements.txt
python manage.py makemigrations 
python manage.py migrate
python manage.py collectstatic --noinput --clear
echo "BUILD END"