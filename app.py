from flask import Flask, render_template, request, redirect, session, send_from_directory
from mysql.connector import Error #Biblioteca para o BD MySQL
from config import *
from db_functions import *
import os
import time

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'upload/'

#Rota da página inicial
@app.route('/')
def index():
    if session:
        if 'adm' in session:
            login = 'adm'
        else:
            login = 'empresa'
    else:
        login = False

    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa'
        ORDER BY vaga.id_vaga DESC LIMIT 9;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL)
        vagas = cursor.fetchall()
        return render_template('index.html', vagas=vagas, login=login)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/vagas')
def vagas():
    if session:
        if 'adm' in session:
            login = 'adm'
        else:
            login = 'empresa'
    else:
        login = False

    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa'
        ORDER BY vaga.id_vaga DESC;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL)
        vagas = cursor.fetchall()
        return render_template('vagas.html', vagas=vagas, login=login)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session:
        if 'adm' in session:
            return redirect('/adm')
        else:
            return redirect('/empresa')

    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        if not email or not senha:  # Corrigi aqui para verificar ambos os campos corretamente
            erro = "Os campos precisam estar preenchidos!"
            return render_template('login.html', msg_erro=erro)

        if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
            session['adm'] = True
            return redirect('/adm')

        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE email = %s AND senha = %s'
            cursor.execute(comandoSQL, (email, senha))
            empresa = cursor.fetchone()

            if not empresa:
                return render_template('login.html', msgerro='E-mail e/ou senha estão errados!')

            # Acessar os dados como dicionário
            if empresa['status'] == 'inativa':
                return render_template('login.html', msgerro='Empresa desativada! Procure o administrador!')

            session['id_empresa'] = empresa['id_empresa']
            session['nome_empresa'] = empresa['nome_empresa']
            return redirect('/empresa')
        
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)
            

@app.route('/adm')
def adm():
    #Se não houver sessão ativa
    if not session:
        return redirect('/login')
    #Se não for o administrador
    if not 'adm' in session:
        return redirect('/empresa')
  
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM Empresa WHERE status = "ativa"'
        cursor.execute(comandoSQL)
        empresas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM Empresa WHERE status = "inativa"'
        cursor.execute(comandoSQL)
        empresas_inativas = cursor.fetchall()

        return render_template('adm.html', empresas_ativas=empresas_ativas, empresas_inativas=empresas_inativas)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/cadastrar_empresa', methods = {'POST','GET'})#Abrir e receber informações de uma nova empresa
def cadastrar_empresa():
    if not session:
        return redirect('/login')

    if not 'adm' in session:
        return redirect('/empresa')

    if request.method == 'GET':
        return render_template('cadastrar_empresa.html')
    
    #Tratando os dados do formulário
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        #Verificar se os campos estão vazios
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('cadastrar_empresa.html', msg_erro = "Todos os campos são obrigatórios!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'INSERT INTO empresa (nome_empresa, cnpj, telefone, email, senha) VALUES (%s, %s, %s, %s, %s)' #Comando para combater o SQL Injection (Falha de segurança) #%S é o especificador de formato
            cursor.execute(comandoSQL, (nome_empresa, cnpj, telefone, email, senha))
            conexao.commit() #Confirmação que o comando seja executado (para INSERT, DELETE e UPDATE)
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062: #"errno" = erro número, o erro 1062 é quando tenta cadastrar algo duplicado como email
                return render_template('cadastrar_empresa.html', msg_erro = "Esse email já existe")
            else:
                return f"Erro de banco de dados: {erro}"
        finally:
            encerrar_db(cursor, conexao)

@app.route('/empresa')
def empresa():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    id_empresa = session['id_empresa']
    nome_empresa = session['nome_empresa']

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "ativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "inativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_inativas = cursor.fetchall()

        return render_template('empresa.html', nome_empresa=nome_empresa, vagas_ativas=vagas_ativas, vagas_inativas=vagas_inativas)         
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/editar_empresa/<int:id_empresa>', methods = ['GET', 'POST'])
def editar_empresa(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session['adm']:
        return redirect('/login')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE id_empresa = %s'
            cursor.execute(comandoSQL, (id_empresa,))
            empresa = cursor.fetchone()
            return render_template('editar_empresa.html', empresa = empresa)
        except Error as erro:
            return f"Erro de banco de dados: {erro}"
        except Exception as erro:
            return f"Erro de back-end: {erro}"
        finally:
            encerrar_db(cursor, conexao)

            #Tratando os dados do formulário
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        #Verificar se os campos estão vazios
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('cadastrar_empresa.html', msg_erro = "Todos os campos são obrigatórios!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
                UPDATE empresa 
                SET nome_empresa = %s, cnpj = %s, telefone = %s, email = %s, senha = %s
                WHERE id_empresa = %s;
                ''' 
            cursor.execute(comandoSQL, (nome_empresa, cnpj, telefone, email, senha, id_empresa))
            conexao.commit() #Confirmação que o comando seja executado (para INSERT, DELETE e UPDATE)
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062: #"errno" = erro número, o erro 1062 é quando tenta cadastrar algo duplicado como email
                return render_template('editar_empresa.html', msg_erro = "Esse email já existe")
            else:
                return f"Erro de banco de dados: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#Rota para ativar ou desativar a empresa
@app.route('/status_empresa/<int:id_empresa>')
def status(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session['adm']:
        return redirect('/login')
    
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        status_empresa = cursor.fetchone()
        if status_empresa['status'] == 'ativa':
            novo_status = 'inativa'
        else:
            novo_status = 'ativa'

        comandoSQL = 'UPDATE empresa SET status = %s WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (novo_status, id_empresa))
        conexao.commit()

        #Se a empresa estiver inativa, as vagas também serão
        if novo_status == 'inativa':
            comandoSQL = 'UPDATE vaga SET status = %s WHERE id_empresa = %s'
            cursor.execute(comandoSQL, (novo_status, id_empresa))
            conexao.commit()
        return redirect('/adm')

    except Error as erro:
        return f"Erro de banco de dados:{erro}"
    except Exception as erro:
        return f"Erro de back-end: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/excluir_empresa/<int:id_empresa>')
def excluir_empresa(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session ['adm']:
        return redirect('/login')
    
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'DELETE FROM vaga WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()

        comandoSQL = 'DELETE FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        return redirect('/adm')
    
    except Error as erro:
        return f"Erro de banco de dados:{erro}"
    except Exception as erro:
        return f"Erro de back-end: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/cadastrar_vaga', methods=['POST','GET'])
def cadastrar_vaga():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')
    
    if request.method == 'GET':
        return render_template('cadastrar_vaga.html')
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = ''
        local = request.form['local']
        salario = ''
        salario = limpar_input(request.form['salario'])
        id_empresa = session['id_empresa']

        if not titulo or not descricao or not formato or not tipo:
            return render_template('cadastrar_vaga.html', msg_erro="Os campos obrigatório precisam estar preenchidos!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO Vaga (titulo, descricao, formato, tipo, local, salario, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_empresa))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)


@app.route('/editar_vaga/<int:id_vaga>', methods=['GET','POST'])
def editarvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM vaga WHERE id_vaga = %s;'
            cursor.execute(comandoSQL, (id_vaga,))
            vaga = cursor.fetchone()
            return render_template('editar_vaga.html', vaga=vaga)
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = request.form['local']
        salario = limpar_input(request.form['salario'])

        if not titulo or not descricao or not formato or not tipo:
            return redirect('/empresa')
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE vaga SET titulo=%s, descricao=%s, formato=%s, tipo=%s, local=%s, salario=%s
            WHERE id_vaga = %s;
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_vaga))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

@app.route("/status_vaga/<int:id_vaga>")
def status_vaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM vaga WHERE id_vaga = %s;'
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        if vaga['status'] == 'ativa':
            status = 'inativa'
        else:
            status = 'ativa'

        comandoSQL = 'UPDATE vaga SET status = %s WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (status, id_vaga))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route("/excluir_vaga/<int:id_vaga>")
def excluir_vaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'DELETE FROM vaga WHERE id_vaga = %s AND status = "inativa"'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/sobre_vaga/<int:id_vaga>')
def sobre_vaga(id_vaga):
    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa 
        WHERE vaga.id_vaga = %s;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        
        if not vaga:
            return redirect('/')
        
        return render_template('sobre_vaga.html', vaga=vaga)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao) 

@app.route('/candidato/<int:id_vaga>', methods=['GET', 'POST'])
def candidato(id_vaga):
    if request.method == 'GET':
       return render_template('candidato.html', id_vaga=id_vaga)
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = limpar_input(request.form['telefone'])
        curriculo = request.files['file']

        if not nome or not email or not telefone or not curriculo:
            return redirect('/candidato', msg_erro="Todos os campos precisam estar preenchidos!")
    
        if curriculo.filename == '':
            msg = "Nenhum arquivo enviado!"
            return render_template('candidato.html', msg=msg)
    
        try:
            timestamp = int(time.time()) #Gera um código
            nome_curriculo = f"{timestamp}_{curriculo.filename}"
            curriculo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_curriculo)) #Salva o arquivo em uma pasta (nuvem)
            conexao, cursor = conectar_db()
            comandoSQL = "INSERT INTO candidato (nome, email, telefone, curriculo, id_vaga) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(comandoSQL, (nome, email, telefone, nome_curriculo, id_vaga,))
            conexao.commit()
            conexao, cursor = conectar_db()
            return redirect(f'/sobre_vaga/{id_vaga}')
        
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA ABRIR O ARQUIVO -- FAZER DOWNLOAD
@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/delete/<filename>')
def delete_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.remove(file_path)  # Exclui o arquivo

        conexao, cursor = conectar_db()
        comandoSQL = "DELETE FROM candidato WHERE curriculo = %s"
        cursor.execute(comandoSQL, (filename,))
        conexao.commit()

        return render_template('/curriculo.html')
    except mysql.connector.Error as erro:
        return f"Erro de banco de Dados: {erro}"
    except Exception as erro:
        return f"Erro de back-end: {erro}"
    finally:
        encerrar_db(conexao, cursor)

@app.route('/lista_empresas')
def lista_empresa():

    try:
        comandoSQL = '''
        SELECT *
        FROM empresa
        WHERE status = 'ativa'
        ORDER BY nome_empresa;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL)
        empresas = cursor.fetchall()
        return render_template('lista_empresas.html', empresas=empresas, login=login)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/curriculo/<int:id_vaga>')
def curriculo(id_vaga):

    if not session:
        return redirect('/login')
    
    if 'adm' in session:
        return redirect ('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM candidato WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (id_vaga,))
        candidatos = cursor.fetchall()
        return render_template('curriculo.html', candidatos=candidatos)

    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

@app.route('/pesquisar', methods=['GET'])
def pesquisar():
    palavra_chave = request.args.get('q', '')
    try:
        conexao, cursor = conectar_db()
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa
        FROM vaga
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa' AND (
            vaga.titulo LIKE %s OR
            vaga.descricao LIKE %s
        )
        '''
        cursor.execute(comandoSQL, (f'%{palavra_chave}%', f'%{palavra_chave}%'))
        vagas = cursor.fetchall()
        return render_template('resultados_pesquisa.html', vagas=vagas, palavra_chave=palavra_chave)
    except Error as erro:
        return f"ERRO! {erro}"
    finally:
        encerrar_db(cursor, conexao)


@app.errorhandler(404)
def not_found(error):
    return render_template('erro404.html'), 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)