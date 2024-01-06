import re
from datetime import datetime
from datetime import date

from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict
from typing import Optional, Literal, Generic
from src.schemas.user import UserResponseSchema


class ContactSchema(BaseModel):
    first_name: str = Field(min_length=3, max_length=32)
    last_name: str = Field(min_length=3, max_length=32)
    email: EmailStr = Field(min_length=8, max_length=64)
    phone_number: str = Field(max_length=24)
    # birth_date: str = Field(min_length=10, max_length=10)
    birth_date: date
    crm_status: Literal['operational', 'analitic', 'corporative'] = 'operational'
    # При створеннi контакту можна не передавати <user>, тому що по маршруту router.post("/", ...) -> [create_contact()]
    # може прийти тiльки аутентифiкований користувач з токеном, тож по токену можна дiстати його <email> та <roles>.

    @validator('phone_number')
    def validate_phone_number(cls, phone):
        if not phone.isdigit():
            raise ValueError('Phone number must contain only digits.')
        return phone
 
    # @validator('birth_date')
    # def validate_birth_date(cls, birth_date):
    #     if len(str(birth_date)) != 10:
    #         raise ValueError('Birth date must contain exactly 10 characters.')
    #     if re.match(r'\d{4}\.\d{2}\.\d{2}', str(birth_date)):
    #         birth_date = datetime.strptime(str(birth_date), '%Y.%m.%d').date()
    #     elif re.match(r'\d{2}\.\d{2}\.\d{4}', str(birth_date)):
    #         birth_date = datetime.strptime(str(birth_date), '%d.%m.%Y').date()
    #     else:
    #         raise ValueError("Incorrect date format, Birth date should be in format [YYYY.MM.DD] or [DD.MM.YYYY].")
    #     if birth_date > date.today():
    #         raise ValueError('Birth date must be in the past.')
    #     return birth_date


class ContactUpdateSchema(ContactSchema):
    pass


class ContactResponseSchema(BaseModel):
    id: int = 1
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birth_date: date
    crm_status: str
    # + в якостi palm-visions
    # поля нижче вiдносяться до класу [Contact]
    created_at: datetime | None
    updated_at: datetime | None
    # можна реалiзувати JOIN за класом [UserResponseSchema] з user.py
    # user: UserResponseSchema | None

    # class Config:
    #     from_orm = True
    model_config = ConfigDict(from_attributes = True)
