from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import requests

from config import TOKEN, TRELLO_API_KEY, TRELLO_TOKEN


# Функция для определения правильного склонения слова в зависимости от числа
def plural_form(n, forms):
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return forms[1]
    else:
        return forms[2]


def start(update, context):
    update.message.reply_text("Привет! Пожалуйста, введите ID доски Trello:")
    return 'GET_BOARD_ID'


def get_board_id(update, context):
    board_id = update.message.text
    context.user_data['board_id'] = board_id
    columns_info = get_columns(board_id)

    if columns_info:
        reply_text = "Список колонок на доске Trello:\n"
        for column_info in columns_info:
            column_name, tasks_count, tasks_word = column_info
            reply_text += f"{column_name}: {tasks_count} {tasks_word}\n"
        update.message.reply_text(reply_text)
    else:
        update.message.reply_text("Не удалось получить информацию о колонках на доске Trello.")

    return ConversationHandler.END


def get_columns(board_id):
    url = f"https://api.trello.com/1/boards/{board_id}/lists?key={TRELLO_API_KEY}&token={TRELLO_TOKEN}"
    response = requests.get(url)

    if response.status_code == 200:
        columns_data = response.json()
        columns_info = []
        for column in columns_data:
            column_name = column['name']
            cards_url = f"https://api.trello.com/1/lists/{column['id']}/cards?key={TRELLO_API_KEY}&token={TRELLO_TOKEN}"
            cards_response = requests.get(cards_url)
            if cards_response.status_code == 200:
                tasks_count = len(cards_response.json())
                tasks_word = plural_form(tasks_count, ['задача', 'задачи', 'задач'])
                columns_info.append((column_name, tasks_count, tasks_word))
            else:
                columns_info.append((column_name, 0, 'задач'))
        return columns_info
    else:
        error_message = f"Ошибка при получении списка колонок: {response.status_code} - {response.reason}"
        print(error_message)
        return []


def cancel(update, context):
    update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            'GET_BOARD_ID': [MessageHandler(Filters.text & ~Filters.command, get_board_id)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
