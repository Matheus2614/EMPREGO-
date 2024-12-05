ambiente = 'desenvolvimento'

if ambiente == 'desenvolvimento':
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'iago'
    DB_NAME = 'emprego'

#Config chave secreta (session)
SECRET_KEY = 'emprego'

#Acesso admin
MASTER_EMAIL = 'adm@adm'
MASTER_PASSWORD = 'adm'