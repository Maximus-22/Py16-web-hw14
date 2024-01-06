from unittest.mock import patch, Mock, AsyncMock, ANY

import pytest
from sqlalchemy import select
from fastapi import status, HTTPException, BackgroundTasks

from src.entity.models import User
from src.repository import users as rep_users
from tests.conftest import TestingSessionLocal, client, get_token
from src.conf import messages
from src.services.auth import auth_service
from src.services.send_email import send_email
from src.conf import messages


user_data = {"username": "gopher", "email": "big-gopher@gmail.com", "password": "1Q2w3e"}


# Увага! Тут [client] та [get_token] - це функцiї з файлу .\tests\conftest.py
def test_signup(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post("api/auth/signup", json=user_data)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data
    assert "avatar" in data


def test_repeat_signup(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post("api/auth/signup", json=user_data)
    assert response.status_code == 409, response.text
    data = response.json()
    assert data["detail"] == messages.ACCOUNT_EXIST


def test_user_not_found_login(client):
    response = client.post("api/auth/login", data={"username": "nonexistent_user@example.com", "password": "pass1029"})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == messages.WRONG_CREDENTIALS

# Цей тест пiдтягується до гори, так як, якщо спочатку провести [test_login], то <user> у тестовiй БД отримає параметр
# user.confirmed = True та у вiдгалуження <not_confirmed_login> ми вже не зайдемо...
def test_not_confirmed_login(client):
    response = client.post("api/auth/login",
                           data={"username": user_data.get("email"), "password": user_data.get("password")})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == messages.EMAIL_NOT_CONFIRMED

@pytest.mark.asyncio
async def test_notverify_password_login(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(select(User).where(User.email == user_data.get("email")))
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()
    response = client.post("api/auth/login", data={"username": user_data["email"], "password": "wrongpas"})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == messages.WRONG_CREDENTIALS

# Тут вже не потрiбно async до БД, оскiльки <user> з user.confirmed = True вже закомiчений
def test_login(client):
    response = client.post("api/auth/login",
                           data={"username": user_data.get("email"), "password": user_data.get("password")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data

# Це додаткова перевiрка - немає <username> = email
def test_validation_error_login(client):
    response = client.post("api/auth/login",
                           data={"password": user_data.get("password")})
    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_refresh_token(client, get_token):
    with patch.object(auth_service, 'cache') as redis_mock:
        redis_mock.get.return_value = None
        email = await auth_service.decode_refresh_token(get_token[1])
        access_token = await auth_service.create_access_token(data={"sub": email, "DB-class": "PSQL"})
        refresh_token = await auth_service.create_refresh_token(data={"sub": email})
        async with TestingSessionLocal() as session:
            current_user = await session.execute(select(User).where(User.email == email))
            current_user = current_user.scalar_one_or_none()
            if current_user:
                current_user.refresh_token = refresh_token
                await session.commit()
        response = client.get("/api/auth/refresh_token", headers={"Authorization": f"Bearer {get_token[1]}"})
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data


def test_refresh_token_invalid_refresh_token(client, get_token):
    with patch.object(auth_service, 'cache') as redis_mock, \
         patch.object(rep_users, 'get_user_by_email') as get_user_mock, \
         patch.object(rep_users, 'update_token') as update_token_mock:

        redis_mock.get.return_value = None
        # Готуємо mock для користувача, який повертається з БД
        user_mock = Mock()
        user_mock.refresh_token = "different_refresh_token"
        get_user_mock.return_value = user_mock

        response = client.get("/api/auth/refresh_token", headers={"Authorization": f"Bearer {get_token[1]}"})

        assert response.status_code == 401
        # Перевіряємо, що функція [update_token] була викликана з очікуваними аргументами
        update_token_mock.assert_called_once_with(user_mock, None, ANY)


def test_confirmed_email(client, get_token):

    # Патчімо функції репозиторію, щоб ізолювати тест від реальної бази даних
    with patch.object(rep_users, 'get_user_by_email') as get_user_mock, \
         patch.object(rep_users, 'confirmed_email') as confirmed_email_mock, \
         patch.object(auth_service, 'get_email_from_token') as get_email_mock:

        # Встановлюємо, що поверне функція [get_email_from_token] під час виклику
        get_email_mock.return_value = messages.TEST_EMAIL

        # Встановлюємо, що поверне функція [get_user_by_email] під час виклику
        # Й припускаємо, що [email] користувача не підтверджено
        get_user_mock.return_value = Mock(confirmed=False)

        # Виконуємо GET-запит на маршрут із підставленим токеном
        response = client.get(f"/api/auth/confirmed_email/{get_token[0]}")

        # Перевіряємо, що функції репозиторію були викликані з правильними аргументами
        # [mock.ANY] можна використовувати для ігнорування аргументу типу AsyncSession
        get_email_mock.assert_called_once_with(get_token[0])
        get_user_mock.assert_called_once_with(messages.TEST_EMAIL, ANY)
        confirmed_email_mock.assert_called_once_with(messages.TEST_EMAIL, ANY)
        assert response.status_code == 200
        # Перевірка, що у відповіді є потрібні елементи
        assert '<h1>Congratulations!</h1>' in response.text


def test_confirmed_email_user_none(client, get_token):
    with patch.object(rep_users, 'get_user_by_email') as get_user_mock:
        # Припускаємо, що користувача не існує
        get_user_mock.return_value = None
        response = client.get(f"/api/auth/confirmed_email/{get_token[0]}")
        assert response.status_code == 400
        assert 'Verification error' in response.text


def test_confirmed_email_already_confirmed(client, get_token):
    with patch.object(rep_users, 'get_user_by_email') as get_user_mock:
        # Припускаємо, що користувача підтверджено
        get_user_mock.return_value = Mock(confirmed=True)  
        response = client.get(f"/api/auth/confirmed_email/{get_token[0]}")
        assert response.status_code == 200
        # Проверяем, что в ответе есть нужные элементы, можно дополнить в соответствии с вашим кодом
        assert '<title>Email already confirmed</title>' in response.text


def test_request_email(client):
    with patch.object(rep_users, 'get_user_by_email') as get_user_mock, \
         patch.object(rep_users, 'confirmed_email') as confirmed_email_mock, \
         patch.object(BackgroundTasks, 'add_task') as add_task_mock:

        get_user_mock.return_value = Mock(email=messages.TEST_EMAIL, username="Deadpool", confirmed=False)

        response = client.post("/api/auth/request_email", json={"email": messages.TEST_EMAIL})

        assert response.status_code == 200
        # Перевіряємо, що функції репозиторію були викликані з правильними аргументами
        # [mock.ANY] можна використовувати для ігнорування аргументу типу AsyncSession
        get_user_mock.assert_called_once_with(messages.TEST_EMAIL, ANY)
        confirmed_email_mock.assert_not_called()
        # Перевіряємо, що функція додавання завдання була викликана
        add_task_mock.assert_called_once_with(send_email, messages.TEST_EMAIL, ANY, ANY)
        # Перевірка, що у відповіді є потрібні елементи
        assert '<p>Check your email for confirmation.</p>' in response.text


def test_request_email_already_confirmed(client):
    with patch.object(rep_users, 'get_user_by_email') as get_user_mock:
        # Встановлюємо, що поверне функція [get_user_by_email] під час виклику
        # Й припускаємо, що [email] користувача не підтверджено
        get_user_mock.return_value = Mock(confirmed=True)  # Предполагаем, что пользователь подтвержден

        response = client.post("/api/auth/request_email", json={"email": messages.TEST_EMAIL})

        assert response.status_code == 200
        assert '<title>Email already confirmed</title>' in response.text