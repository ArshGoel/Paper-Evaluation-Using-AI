echo "BUILD START"
python -m pip install requirements.txt
python -m manage.py makemigrations 
python -m manage.py migrate
python manage.py collectstatic --noinput --clear
echo "BUILD END"