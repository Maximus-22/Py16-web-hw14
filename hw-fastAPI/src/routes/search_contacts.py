from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository import contacts as rep_contacts
from src.schemas.contact import ContactSchema, ContactUpdateSchema, ContactResponseSchema
from src.entity.models import User, Role
from src.services.auth import auth_service
from src.services.roles import RoleAccess

router = APIRouter(prefix='/search', tags=['search'])

# Цей функтор буде пропускати тiльки тi запити, ролi в користувачiв яких спiвпадають
access_elevated = RoleAccess([Role.admin, Role.moderator])


""" У цьому місці реалізовано опціональний вибір пошуку по одному з полів - за кожне поле
    відповідає окрема функція """
# @router.get("/", response_model=list[ContactResponseSchema])
# async def search_contact_by_field(
#     first_name: Optional[str] = Query(None, description="Ім'я контакту"),
#     last_name: Optional[str] = Query(None, description="Прізвище контакту"),
#     email: Optional[str] = Query(None, description="Електронна адреса контакту"),
#     db: AsyncSession = Depends(get_db)):
#     if first_name:
#         return await rep_contacts.search_contact_by_firstname(first_name, db)
#     elif last_name:
#         return await rep_contacts.search_contact_by_lastname(last_name, db)
#     elif email:
#         return await rep_contacts.search_contact_by_email(email, db)
#     else:
#         raise ValueError("Необхідно вказати: ім'я, прізвище або e-mail контакту.")


""" У цьому випадку Path(..., <default>, <title>, <description>) означає, що параметр
    <contact_first_name> є обов'язковим і повинен бути вказаний в [URL]. Якщо параметр не вказано,
    буде викликано виняток. """
@router.get("/by_firstname/{contact_first_name}", response_model=list[ContactResponseSchema])
async def search_contact_by_firstname(contact_first_name: str = Path(..., description="Ім'я контакту"),
                              db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    """
    The search_contact_by_firstname function searches for contacts by first name.
        The search_contact_by_firstname function is a GET request that takes in the contact's first name as a parameter.
        It returns all contacts with the given first name.
    
    :param contact_first_name: str: Pass the contact's first name to the function
    :param description: Describe the parameter in the openapi documentation
    :param db: AsyncSession: Get the database session
    :param user: User: Get the current user
    :return: A list of contacts
    :doc-author: Trelent
    """
    contacts = await rep_contacts.search_contact_by_firstname(contact_first_name, db)
    return contacts

@router.get("/by_lastname/{contact_last_name}", response_model=list[ContactResponseSchema])
async def search_contact_by_lastname(contact_last_name: str = Path(..., description="Прізвище контакту"),
                              db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    """
    The search_contact_by_lastname function allows you to search for a contact by last name.
    
    :param contact_last_name: str: Pass the contact's last name to the function
    :param description: Describe the parameter in the documentation
    :param db: AsyncSession: Get the database session
    :param user: User: Identify the user who is logged in
    :return: A list of contacts
    :doc-author: Trelent
    """
    contacts = await rep_contacts.search_contact_by_lastname(contact_last_name, db)
    return contacts

@router.get("/by_email/{contact_email}", response_model=list[ContactResponseSchema])
async def search_contact_by_email(contact_email: str = Path(..., description="Електронна адреса контакту"),
                              db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    """
    The search_contact_by_email function searches for a contact by email.
    
    :param contact_email: str: Get the email of the contact we want to search for
    :param description: Describe the parameter in the openapi documentation
    :param db: AsyncSession: Pass the database connection to the function
    :param user: User: Get the current user from the database
    :return: A list of contacts
    :doc-author: Trelent
    """
    contacts = await rep_contacts.search_contact_by_email(contact_email, db)
    return contacts


# Знайдена міцна залежність між шляхом {value} та назвою змінної у функції -> search_contact_complex(value, ... 
@router.get("/by_complex/{value}", response_model=list[ContactResponseSchema], dependencies=[Depends(access_elevated)])
async def search_contact_complex(value: str = Path(..., description="Здійснює пошук у полях контакту: Ім'я, Прізвище та Електронна адреса"),
                              db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    """
    The search_contact_complex function is used to search for contacts by name, surname and email.
        The function takes a string value as an argument and returns a list of contacts that match the search criteria.
    
    :param value: str: Search for a contact in the database
    :param description: Describe the endpoint in the openapi documentation
    :param Прізвище та Електронна адреса&quot;): Search for a contact by surname and email
    :param db: AsyncSession: Get the database session
    :param user: User: Get the current user from the database
    :return: A list of contacts
    :doc-author: Trelent
    """
    contacts = await rep_contacts.search_contact_complex(value, db)
    return contacts