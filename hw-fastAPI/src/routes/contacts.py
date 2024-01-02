from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository import contacts as rep_contacts
from src.entity.models import User, Role
from src.schemas.contact import ContactSchema, ContactUpdateSchema, ContactResponseSchema
from src.services.auth import auth_service
from src.services.roles import RoleAccess

router = APIRouter(prefix='/contacts', tags=['contacts'])

# Цей функтор буде пропускати тiльки тi запити, ролi в користувачiв яких спiвпадають
access_elevated = RoleAccess([Role.admin, Role.moderator])


@router.get("/", response_model=list[ContactResponseSchema], description="No more than 10 requests per minute",
            dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_contacts(limit: int = Query(10, ge=10, le=500), offset: int = Query(0, ge=0),
                    db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    """
    The get_contacts function returns a list of contacts.
        The limit and offset parameters are used to paginate the results.
        The user parameter is used to get only the contacts for that user.
    
    :param limit: int: Limit the number of contacts returned
    :param ge: Specify that the limit must be greater than or equal to 10
    :param le: Set the maximum value of the limit parameter
    :param offset: int: Specify the number of records to skip
    :param ge: Set a minimum value for the limit parameter
    :param db: AsyncSession: Get the database connection
    :param user: User: Get the current user
    :return: A list of contacts
    :doc-author: Trelent
    """
    contact = await rep_contacts.get_contacts(limit, offset, db, user)
    return contact



@router.get("/all", response_model=list[ContactResponseSchema], dependencies=[Depends(access_elevated)])
async def get_contacts_all(limit: int = Query(10, ge=10, le=500), offset: int = Query(0, ge=0),
                    db: AsyncSession = Depends(get_db), user: User = Depends(auth_service.get_current_user)):
    """
    The get_contacts_all function returns a list of contacts.
        The limit and offset parameters are used to paginate the results.
        The user parameter is used to determine if the current user has access to this endpoint.
    
    :param limit: int: Limit the number of results returned
    :param ge: Specify the minimum value of the parameter
    :param le: Set the maximum value of a parameter
    :param offset: int: Skip the first n records
    :param ge: Specify the minimum value that is allowed
    :param db: AsyncSession: Get the database session
    :param user: User: Get the user id from the jwt token
    :return: All contacts in the database
    :doc-author: Trelent
    """
    contact = await rep_contacts.get_contacts_all(limit, offset, db)
    return contact


@router.get("/{contact_id}", response_model=ContactResponseSchema, description="No more than 10 requests per minute",
            dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_contact(contact_id: int = Path(ge=1), db: AsyncSession = Depends(get_db),
                      user: User = Depends(auth_service.get_current_user)):
    """
    The get_contact function is used to retrieve a single contact from the database.
    It takes an integer as its only argument, which represents the ID of the contact
    to be retrieved. It returns a Contact object.
    
    :param contact_id: int: Specify the id of the contact to be retrieved
    :param db: AsyncSession: Get the database session
    :param user: User: Get the current user from the auth_service
    :return: The contact object with the given id
    :doc-author: Trelent
    """
    contact = await rep_contacts.get_contact(contact_id, db, user)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ENTITY NOT FOUND.")
    return contact


@router.post("/", response_model=ContactResponseSchema, status_code=status.HTTP_201_CREATED,
             description="No more than 3 injections per minute", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
async def create_contact(body: ContactSchema, db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)):
    """
    The create_contact function creates a new contact in the database.
        It takes a ContactSchema object as input, and returns the newly created contact.
        The user who is creating this contact must be logged in.
    
    :param body: ContactSchema: Validate the request body
    :param db: AsyncSession: Get the database session
    :param user: User: Get the current user
    :return: A contact object
    :doc-author: Trelent
    """
    contact = await rep_contacts.create_contact(body, db, user)
    return contact


@router.put("/{contact_id}", description="No more than 5 requests per minute",
            dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def update_contact(body: ContactSchema, contact_id: int = Path(ge=1), db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)):
    """
    The update_contact function updates a contact in the database.
        It takes an id, body and db as parameters. The id is used to find the contact in the database,
        while body contains all of the information that will be updated for that contact. 
        
        Args: 
    
    :param body: ContactSchema: Get the data from the request body
    :param contact_id: int: Get the contact id from the url
    :param db: AsyncSession: Pass the database connection to the function
    :param user: User: Get the current user from the auth_service
    :return: The contact that was updated
    :doc-author: Trelent
    """
    contact = await rep_contacts.update_contact(contact_id, body, db, user)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ENTITY NOT FOUND.")
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, description="No more than 3 graveyards per minute",
            dependencies=[Depends(RateLimiter(times=3, seconds=60))])
async def delete_contact(contact_id: int = Path(ge=1), db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)):
    """
    The delete_contact function deletes a contact from the database.
        The function takes in an integer representing the id of the contact to be deleted,
        and returns a dictionary containing information about that contact.
    
    :param contact_id: int: Specify the contact_id of the contact to be deleted
    :param db: AsyncSession: Pass the database session to the function
    :param user: User: Get the current user from the auth_service
    :return: The deleted contact
    :doc-author: Trelent
    """
    contact = await rep_contacts.delete_contact(contact_id, db, user)
    return contact
