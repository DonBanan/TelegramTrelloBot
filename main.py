import requests
from collections import defaultdict

from telegram import ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton

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
        keyboard = []
        for column_name in columns_info:
            keyboard.append([KeyboardButton(column_name)])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        update.message.reply_text("Выберите колонку:", reply_markup=reply_markup)
        return 'GET_COLUMN'
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
            columns_info.append((column_name))
        return columns_info
    else:
        error_message = f"Ошибка при получении списка колонок: {response.status_code} - {response.reason}"
        print(error_message)
        return []


def get_column(update, context):
    selected_column = update.message.text
    board_id = context.user_data['board_id']
    columns_info = get_columns(board_id)
    column_id = None
    for column_name in columns_info:
        if column_name == selected_column:
            column_id = column_name
            break

    if column_id:
        members_info = get_members_in_column(board_id, column_id)
        reply_text = f"Список сотрудников и количество их задач в колонке '{selected_column}':\n"

        label_tasks = defaultdict(int)
        for _, label_name, tasks_count in members_info:
            label_tasks[label_name] += tasks_count

        for member_name, _, _ in members_info:
            member_tasks = [f"{label}: {label_tasks[label]}" for label in label_tasks]
            member_tasks_str = " | ".join(member_tasks)
            reply_text += f"*{member_name}:* {member_tasks_str}\n"
            break  # Прерываем цикл после первой итерации, чтобы выводилось только одно имя

        update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text("Колонка не найдена. Пожалуйста, выберите колонку из предложенных кнопок.")

    return ConversationHandler.END


def get_members_in_column(board_id, column_name):
    url = f"https://api.trello.com/1/boards/{board_id}/lists?key={TRELLO_API_KEY}&token={TRELLO_TOKEN}"
    response = requests.get(url)

    if response.status_code == 200:
        columns_data = response.json()
        for column in columns_data:
            if column['name'] == column_name:
                cards_url = f"https://api.trello.com/1/lists/{column['id']}/cards?key={TRELLO_API_KEY}&token={TRELLO_TOKEN}&members=true"
                cards_response = requests.get(cards_url)
                if cards_response.status_code == 200:
                    cards_data = cards_response.json()
                    members_tasks_count = {}
                    for card in cards_data:
                        for member_id in card['idMembers']:
                            member_name = get_member_name(member_id)
                            for label in card.get('labels', []):
                                label_name = label['name']
                                # Формируем HTML-разметку для изменения цвета текста
                                colored_label_name = f"**{label_name}**"
                                members_tasks_count.setdefault((member_name, colored_label_name), 0)
                                members_tasks_count[(member_name, colored_label_name)] += 1

                    members_info = []
                    for (member_name, colored_label_name), tasks_count in members_tasks_count.items():
                        members_info.append((member_name, colored_label_name, tasks_count))
                    return members_info
                else:
                    error_message = f"Ошибка при получении списка карточек: {cards_response.status_code} - {cards_response.reason}"
                    print(error_message)
                    return []
    else:
        error_message = f"Ошибка при получении списка колонок: {response.status_code} - {response.reason}"
        print(error_message)
        return []


def get_member_name(member_id):
    url = f"https://api.trello.com/1/members/{member_id}?key={TRELLO_API_KEY}&token={TRELLO_TOKEN}"
    response = requests.get(url)
    if response.status_code == 200:
        member_data = response.json()
        return member_data.get('fullName', 'Неизвестный сотрудник')
    else:
        print(f"Ошибка при получении данных сотрудника: {response.status_code} - {response.reason}")
        return 'Неизвестный сотрудник'


def cancel(update, context):
    update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            'GET_BOARD_ID': [MessageHandler(Filters.text & ~Filters.command, get_board_id)],
            'GET_COLUMN': [MessageHandler(Filters.text & ~Filters.command, get_column)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()