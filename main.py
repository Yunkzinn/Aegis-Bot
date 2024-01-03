import os
import subprocess
import telebot
from telebot import types

# Inicializar o bot do Telegram
bot = telebot.TeleBot('TOKEN_API_TELEGRAM')

# Dicionário para armazenar senhas associadas aos IDs de usuário
senha_por_usuario = {}

# Dicionário para armazenar informações sobre a varredura em andamento
varredura_em_andamento = {}

# Comando "/start"
@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.id not in senha_por_usuario:
        # Se o usuário não tiver uma senha definida, enviar uma mensagem de boas-vindas e solicitar a senha
        bot.send_message(message.chat.id, 'Bem-vindo! Por favor, digite a senha:')
    else:
        # Se o usuário já tiver uma senha definida, mostrar os botões
        show_buttons(message.chat.id)

# Manipulador para mensagens de texto
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if chat_id not in senha_por_usuario:
        # Se o usuário não tiver uma senha definida, verificar a senha fornecida
        verificar_senha(message)
    else:
        # Se o usuário já tiver uma senha definida, processar comandos
        processar_comandos(message)

# Função para verificar a senha
def verificar_senha(message):
    senha_correta = 'YOUR_PASSWORD'  # Substituir com sua senha real
    senha_digitada = message.text.strip()

    if senha_digitada == senha_correta:
        # Se a senha estiver correta, definir a senha para o usuário e mostrar os botões
        senha_por_usuario[message.chat.id] = senha_correta
        show_buttons(message.chat.id)
    else:
        # Se a senha estiver incorreta, enviar uma mensagem de erro
        bot.reply_to(message, 'Senha incorreta. Tente novamente.')

# Função para mostrar os botões
def show_buttons(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_scan = types.KeyboardButton('Scan')  # Alteração aqui
    btn_cancel = types.KeyboardButton('Cancel')
    markup.row(btn_scan, btn_cancel)
    bot.send_message(chat_id, 'Senha correta! Pressione o botão "Scan" para iniciar a varredura ou o botão "/cancel" para interromper.', reply_markup=markup)

# Função para processar comandos
def processar_comandos(message):
    chat_id = message.chat.id
    if message.text == 'Scan':  # Alteração aqui
        # Se o comando for Scan, solicitar o domínio
        bot.reply_to(message, 'Por favor, forneça o domínio que deseja escanear.')
        # Salvar informações sobre a varredura em andamento
        varredura_em_andamento[chat_id] = {'url': None, 'domain': None}
    elif message.text == 'Cancel':
        # Se o comando for Cancel, chamar a função handle_cancel_command
        handle_cancel_command(message)
    elif chat_id in varredura_em_andamento and varredura_em_andamento[chat_id]['url'] is None:
        # Se não for um comando reconhecido e houver uma varredura em andamento sem URL definida, considerar a mensagem como o domínio
        handle_domain(message)
    else:
        # Qualquer outro comando ou mensagem recebida
        bot.reply_to(message, 'Comando não reconhecido. Por favor, use os botões fornecidos.')

# Manipulador para mensagens contendo domínio
def handle_domain(message):
    chat_id = message.chat.id
    if chat_id in varredura_em_andamento and varredura_em_andamento[chat_id]['url'] is None:
        # Verificar se a mensagem contém um domínio
        domain = message.text.strip()

        # Salvar o domínio para a varredura em andamento
        varredura_em_andamento[chat_id]['domain'] = domain

        # Chamar a função de varredura
        handle_scan_command(message)

# Comando "/scan"
def handle_scan_command(message):
    chat_id = message.chat.id

    # Verificar se há uma varredura em andamento para este chat_id
    if chat_id not in varredura_em_andamento:
        bot.reply_to(message, 'Nenhuma varredura em andamento.')
        return

    # Obter informações sobre a varredura em andamento
    domain = varredura_em_andamento[chat_id]['domain']

    # Criar uma pasta com o nome da URL
    folder_name = domain.replace('://', '_').replace('/', '_')
    os.makedirs(folder_name, exist_ok=True)

    try:
        # Enviar mensagem de resposta inicial
        bot.reply_to(message, f'Iniciando a varredura em {domain}...')

        # Definir o diretório de trabalho como a pasta da URL
        os.chdir(folder_name)

        # Executar as ferramentas
        subprocess.run(['subfinder', '-d', domain, '-o', 'subdomains.txt', '-silent'], capture_output=True)
        subprocess.run(['naabu', '-host', domain, '-o', 'ports.txt', '-silent'], capture_output=True)

        # Executar o comando wc -l para contar os subdomínios
        resultado_wc_sub = subprocess.run(['wc', '-l', 'subdomains.txt'], capture_output=True, text=True)

        # Extrair o número de subdomínios do resultado
        numero_subdominios = resultado_wc_sub.stdout.strip().split()[0]

        # Enviar mensagem com a contagem de subdomínios
        mensagem_contagem_sub = f'Encontrei um total de {numero_subdominios} subdomínios.'
        bot.send_message(chat_id, mensagem_contagem_sub)

        # Executar o comando wc -l para contar as portas
        resultado_wc_port = subprocess.run(['wc', '-l', 'ports.txt'], capture_output=True, text=True)

        # Extrair o número de portas do resultado
        numero_ports = resultado_wc_port.stdout.strip().split()[0]

        # Enviar mensagem com a contagem de portas
        mensagem_contagem_ports = f'Encontrei um total de {numero_ports} portas abertas.'
        bot.send_message(chat_id, mensagem_contagem_ports)

        # Enviar mensagem de conclusão
        bot.reply_to(message, 'Varredura concluída!')
    except Exception as e:
        # Se ocorrer algum erro, enviar uma mensagem de erro
        bot.reply_to(message, f'Ocorreu um erro durante a varredura: {str(e)}')
    finally:
        # Independentemente do resultado, voltar ao diretório anterior e limpar as informações de varredura
        os.chdir('..')
        if os.path.exists(folder_name):
            os.rmdir(folder_name)
        del varredura_em_andamento[chat_id]

# Comando "Cancel"
@bot.message_handler(commands=['cancel'])
def handle_cancel_command(message):
    chat_id = message.chat.id
    if chat_id in varredura_em_andamento:
        # Limpar o chat
        bot.send_message(chat_id, 'Varredura cancelada. Limpando o chat...')
        bot.delete_message(chat_id, message.message_id)

        # Interromper a varredura
        os.chdir('..')  # Voltar ao diretório anterior
        folder_name = varredura_em_andamento[chat_id]['folder_name']
        if os.path.exists(folder_name):
            os.rmdir(folder_name)  # Remover a pasta da varredura
        del varredura_em_andamento[chat_id]
    else:
        bot.reply_to(message, 'Nenhuma varredura em andamento para cancelar.')

# Tratamento de exceções para evitar que erros interrompam o polling
try:
    # Iniciar o bot
    bot.infinity_polling()
except Exception as e:
    print(f'Ocorreu um erro no bot: {str(e)}')
