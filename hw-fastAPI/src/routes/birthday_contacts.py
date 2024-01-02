from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.entity.models import User, Role
from src.repository import contacts as rep_contacts
from src.schemas.contact import ContactSchema, ContactUpdateSchema, ContactResponseSchema
from src.services.auth import auth_service
from src.services.roles import RoleAccess

router = APIRouter(prefix='/birthday', tags=['birthday'])

# Цей функтор буде пропускати тiльки тi запити, ролi в користувачiв яких спiвпадають
access_elevated = RoleAccess([Role.admin, Role.moderator])


# Знайдена міцна залежність між шляхом {shift_days} та назвою змінної у функції -> search_contact_by_birthdate(shift_days, ... 
@router.get("/{shift_days}", response_model=list[ContactResponseSchema], dependencies=[Depends(access_elevated)])
async def search_contact_by_birthdate(shift_days: int = Path(..., description="Кількість найближчих днів у запитi"),
                                      db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    """
    The search_contact_by_birthdate function is used to search contacts by birthdate.
        The function takes a shift_days parameter, which is the number of days from today's date.
        For example, if shift_days = 7, then the function will return all contacts whose birthday falls within the next week.
    
    :param shift_days: int: Specify the number of days to search for contacts
    :param description: Describe the parameter in the documentation
    :param db: AsyncSession: Get the database session
    :param user: User: Get the current user from the database
    :return: The list of contacts, which birthday is in the next shift_days days
    :doc-author: Trelent
    """
    contacts = await rep_contacts.search_contact_by_birthdate(shift_days, db)
    return contacts