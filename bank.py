import re                                       #Импортирует модуль регулярных выражений для проверки корректности паролей.
import json                                     #Импортирует модуль JSON для работы с файлом данных в формате JSON.
from datetime import datetime, timedelta        #Импортирует классы для работы с датами и временем.
import logging                                  #Импортирует модуль для логирования ошибок
from twilio.rest import Client                  #Импортирует модуль для отправки SMS-уведомлений через Twilio API.



def current_datetime():
    current_datetime = (datetime.now() + timedelta(hours=0)).strftime("%Y-%m-%d %H:%M:%S")
    return current_datetime


logging.basicConfig(filename="errors.log", level=logging.ERROR, format="%(levelname)s - %(message)s")


class FileWorker:
    def read_json(self): #Читает данные из файла JSON в словарь
        with open("data.json") as f:
            return json.load(f)

    def convert_user(self, user):  #Преобразует данные пользователя из словаря в объект класса User.
        return User(
            user["username"],
            user["password"],
            user["deposit"],
            user["transactions"],
            phone_number=user.get("phone_number", '')
        )

    def convert_users(self, users): #Преобразует список пользователей из словарей в список объектов User.
        new_users = []
        for user in users:
            new_user = self.convert_user(user)
            new_users.append(new_user)
        return new_users

    def get_users_and_current_user(self):  #Возвращает список пользователей и имя текущего пользователя из файла JSON.
        data = self.read_json()
        current_user = data["current_user"]
        users = self.convert_users(data["users"])
        return users, current_user

    def update_json(self, users, current_user): #Сохраняет данные пользователей и текущего пользователя в файл JSON.
        with open("data.json", "w") as f:
            json.dump({
                "users": [user.convert_to_json() for user in users],
                "current_user": current_user
            }, f)


class BankSystem(FileWorker):
    def __init__(self, name): #Инициализирует систему с указанным именем.
        self._name = name
        self._users, self._current_user = self.get_users_and_current_user()

    def print_commands(self): #Выводит список доступных команд в зависимости от того, вошел ли пользователь в систему.
        if self._current_user is None:
            print(
                "\nEnter commands below:\n  login : to log in to the system.\n  create: to create an account.\n  exit: to exit the system.\n")
        else:
            print(
                "\nEnter commands below:\n  top_up -1: to top up deposit.\n  check_deposit -2: to check your deposit.\n  transactions-3: to view all your transactions.\n  transfer-4: to transfer money to another user.\n  logout-5: to log out of the system.\n  exit -6: to exit the system.\n")

    def registration(self): #Регистрирует нового пользователя.
        print("\nPlease enter the following information to create an account:\n")
        while True:
            username = input("Create a username: ").lower().strip()
            password = input("Create a password(min 8 chars): ")
            phone_number = input("Enter your phone number: ")
            # add a feature to check password twice

            if self.check_user_by_username(username):
                logging.error(f"{current_datetime()} - Username {username} already exists.")
                print("This username already exists. Try entering a different username!")
                continue
            elif self.is_empty(username):
                logging.error(f"{current_datetime()} - Username {username} is empty.")
                print(f"Username {username} is empty. Try entering a different username!")
                continue
            elif not self.is_valid_password(password):
                logging.error(f"Password '{password}' is not valid")
                print("There are not enough characters in this password or contain forbidden characters!")
                continue

            new_user = User(username, password, phone_number=phone_number)
            self.update_users_list(new_user)
            self.update_current_user(username)
            print("You have successfully created an account!")
            break

    def login(self): #Осуществляет вход пользователя в систему.
        print("\nPlease, enter the data in the cells below to Log in the system!")
        while True:
            user_login = input("Login: ").lower().strip()
            user_password = input("Password: ")
            if self.check_login(user_login, user_password):
                self.update_current_user(user_login)
                print(f"\nWelcome to the bank, {user_login.capitalize()}!")
                break
            else:
                logging.error(f"Login '{user_login}' or password '{user_password}' are incorrect")
                print("Login  or password is wrong! try again.")
                continue

    def logout(self): #Выполняет выход пользователя из системы.
        self.update_current_user(None)
        print("You just logged out successfully")

    def check_login(self, user_login, password): #Проверяет правильность логина и пароля.
        for user in self._users:
            if user.get_username() == user_login and user.check_password(password) and len(user_login) > 0:
                return True
        return False

    def get_user_by_username(self, username): #Возвращает пользователя по его имени пользователя.
        for user in self._users:
            if user.get_username() == username:
                return user
        return None

    def check_deposit(self): # Выводит текущий депозит пользователя
        user = self.get_user_by_username(self._current_user)
        print(f"\nDeposit: {user.get_deposit()} tenge!")

    def check_user_by_username(self, username): #Проверяет, существует ли пользователь с указанным именем.
        if self.get_user_by_username(username):
            return True
        return False

    def is_empty(self, string): # Проверяет, является ли строка пустой.
        return len(string) == 0

    def is_valid_password(self, password): # Проверяет правильность пароля.
        pattern = re.compile(r'[^\w\d*()<>?/\|}{~ ]')
        return not bool(pattern.search(password)) and len(password) >= 8

    def has_access(self): #Возвращает True, если пользователь вошел в систему.
        return self._current_user is not None

    def top_up(self): #Пополняет депозит пользователя.
        while True:
            user = self.get_user_by_username(self._current_user)
            money = input("\nHow much money do you want to deposit?\n> ")
            if not self.is_valid(money):
                logging.error(f"{current_datetime()} - Invalid input: {money}")
                print("You have entered an invalid value. Try again!")
                if not self.ask_retry():
                    break
                continue

            money = int(money)
            user = self.get_user_by_username(self._current_user)
            user.set_deposit(money)
            transaction = f"You topped {money} tenge up at {current_datetime()} to the deposit."
            self.send_sms_notification(user.get_phone_number(), transaction)
            user.set_transaction(transaction)
            self.update_json(self._users, self._current_user)
            print(f"You successfully deposited money to your deposit!")
            print(f"Now, you have {user.get_deposit()} tenge on your deposit!")
            break

    def show_transactions(self):  # Выводит список всех транзакций пользователя.
        user = self.get_user_by_username(self._current_user)
        transactions = user.get_transactions()
        if not transactions:
            print("\nThere are no transactions yet!")
        else:
            print("\nAll your transactions:")
            for transaction in transactions:
                print(transaction)

    def transfer(self): #Осуществляет перевод денег между пользователями.
        while True:
            if len(self._users) == 1:
                print("\nThere is only one user in the system. You can't transfer money!")
                break
            self.list_of_all_users()
            recipient_username = input("\nWho do you want to transfer money to?\n> ").strip().lower()
            recipient = self.get_user_by_username(recipient_username)
            sender_username = self._current_user

            if recipient is None:
                logging.error(f"{current_datetime()} - Invalid input: {recipient_username}")
                print("User not found! Try again!")
                if not self.ask_retry():
                    break
                continue

            while True:
                money = input("How much money do you want to transfer?\n > ")
                if self.is_valid(money):
                    money = int(money)
                    sender_user = self.get_user_by_username(sender_username)
                    if money > sender_user.get_deposit():
                        logging.error(
                            f"User: '{sender_user.get_username()}' doesn't have enough money to transfer '{money}' tenge!")
                        print("You do not have enough money to transfer!")
                        if not self.ask_retry():
                            break
                        continue

                    self.transfer_money(recipient_username, sender_username, money)

                    break
                else:
                    logging.error(f"{sender.get_username}. Invalid input: {money}")
                    print("You enter an invalid number!")
                    if not self.ask_retry():
                        break
                    continue
            break

    def transfer_money(self, recipient, sender, money):
        money = int(money)
        recipient_user = self.get_user_by_username(recipient)
        sender_user = self.get_user_by_username(sender)
        if recipient_user is None:
            return
        recipient_user.set_deposit(money)
        sender_user.set_deposit(-money)

        transaction_rec = f"Receipt of {money} tenge from {sender_user.get_username()} at {current_datetime()}"
        transaction_send = f"Transfer of {money} tenge to {recipient_user.get_username()} at {current_datetime()}."
        recipient_user.set_transaction(transaction_rec)
        sender_user.set_transaction(transaction_send)
        self.update_json(self._users, self._current_user)
        print("You transferred successfully!")

    def list_of_all_users(self): #Выводит список всех пользователей системы.
        print("\nList of all users for transfer: ")
        for user in self._users:
            counter = 1
            if user.get_username() != self._current_user:
                print(f" {counter}: {user.get_username()}")
                counter += 1

    def ask_retry(self):  #Спрашивает пользователя, хочет ли он повторить операцию.
        while True:
            user_choice = input("Enter 'yes' to try again or 'no' to cancel: ").lower().strip()
            if user_choice == "yes":
                return True
            elif user_choice == "no":
                return False
            else:
                logging.error(f"User choice '{user_choice} is not valid!'")
                print("Invalid choice. Please enter 'yes' or 'no'.")

    def is_valid(self, money): #Проверяет, является ли введенная сумма денег валидной.
        return money.isdigit() and int(money) >= 0

    def update_users_list(self, user): #Обновляет список пользователей в системе.
        self._users.append(user)
        self.update_json(self._users, self._current_user)

    def update_current_user(self, current_user): #Обновляет информацию о текущем пользователе.
        self._current_user = current_user
        self.update_json(self._users, self._current_user)

    def send_sms_notification(self, recipient_number, transfer_message): #Отправляет SMS-уведомление о переводе денег.
        # настройки Twilio API
        account_sid = 'AC949920507ec0725a90148b857b994e8c'
        auth_token = 'c73ee395c48db4e0d74d0ec0846019c1'

        client = Client(account_sid, auth_token)

        twilio_number = '+19038415086'
        recipient_number = f'{recipient_number}'

        try:
            message = client.messages.create(
                from_=twilio_number,
                body=transfer_message,
                to=recipient_number
            )
            print(f"SMS sent to {recipient_number}: {message.sid}")
        except Exception as e:
            print(f"Error sending SMS: {e}")
            logging.error(f"Error sending SMS: {e}")


class User:
    def __init__(self, username, password, deposit=0, transactions=None, phone_number=''):  #Инициализирует пользователя с указанными данными.
        self._username = username
        self._password = password
        self._deposit = deposit
        self._transactions = transactions if transactions is not None else []
        self._phone_number = phone_number

    def get_username(self): #Возвращает имя пользователя.
        return self._username

    def get_deposit(self): # Возвращает депозит пользователя.
        return self._deposit

    def set_deposit(self, money): #Устанавливает депозит пользователя.
        self._deposit += money

    def get_transactions(self): # Возвращает список транзакций пользователя.
        return self._transactions

    def set_transaction(self, transaction): #Добавляет транзакцию в список транзакций пользователя.
        self._transactions.append(transaction)

    def get_phone_number(self): # Возвращает номер телефона пользователя.
        return self._phone_number

    def convert_to_json(self): #Преобразует данные пользователя в словарь для сохранения в JSON.
        return {
            "username": self._username,
            "password": self._password,
            "deposit": self._deposit,
            "transactions": self._transactions,
            "phone_number": self._phone_number
        }

    def check_password(self, password): #Проверяет правильность пароля.
        return self._password == password
