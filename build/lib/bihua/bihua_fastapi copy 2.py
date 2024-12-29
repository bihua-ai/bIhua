from fastapi import FastAPI,HTTPException, status, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import os, shutil, subprocess, utilities

from dotenv import load_dotenv
from contextlib import asynccontextmanager

import bihua_one_star, bihua_api, messenger_resident, messenger_group
from messenger_resident import Resident
from messenger_group import Group
from bihua_logging import get_logger
from bihua_one_star import Star
from status_definitions import RegisterStatus, CheckCrudStatus, LoginStatus, CrudStatus
from nio import AsyncClient

logger = get_logger()

@asynccontextmanager
async def lifespan(bihua: FastAPI):
    # Startup logic
    await setup()
    yield
    # Shutdown logic (if needed)
    logger.info("Bihua service is shutting down.")

bihua = FastAPI(
    lifespan=lifespan  # Use lifespan context manager
)

# uvicorn bihua_fastapi:bihua --host 0.0.0.0 --port 8100 --reload

# Add CORS middleware to allow access from all origins
bihua.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows access from all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# Setup function to be run on startup
async def setup():
    # Load environment variables from .env file
    _star = Star()
    
    logger.info("FastAPI service starting up...")

    try:
        # Attempt to login and retrieve access token
        logger.info(f"Attempting to login as {_star.messenger_admin_id}...")
        admin_access_token = _star.messenger_admin_access_token
        if admin_access_token == "":
            client = AsyncClient(_star.messenger_server_url, _star.messenger_admin_id)
            await client.login(_star.messenger_admin_password)  # Await the login process
            admin_access_token = client.access_token
            client.logout()
            await client.close()

        if not admin_access_token:
            logger.error("Failed to retrieve access token from the messenger server.")
            raise ValueError("Access token not retrieved.")
        else:
            logger.info(f"{_star.messenger_admin_id} has logged in...")
            _star.messenger_admin_access_token = admin_access_token
            # _star.update_setting("messenger_admin_access_token", admin_access_token)
            utilities.update_env_file("ADMIN_ACCESS_TOKEN", f"\"{admin_access_token}\"")

        # save admin json profile.
        _resident = Resident(_star.messenger_admin_id)
        _resident.settings.access_token = admin_access_token
        messenger_resident.resident_settings_save(_resident.settings)

        # take care text profile
        load_status, profile_text = _resident.resident_text_profile_load()
        if load_status != CheckCrudStatus.SUCCESS: # initialization is needed.
            profile_text = "Please enter agent profile text here..."
            _resident.resident_text_profile_create_or_update(profile_text=profile_text)


        setting_status = messenger_resident.sync_and_save_all_resident_settings()
        if setting_status != CrudStatus.SUCCESS:
            logger.error(f"Error during setup: Failed  to collect and save resident's profiles.")
            raise  # Re-raise exception after logging
        messenger_resident.generate_resident_json_list() # overwrite existing if there is one

        setting_status = messenger_group.sync_and_save_groups_settings()
        if setting_status != CrudStatus.SUCCESS:
            logger.error(f"Error during setup: Failed  to collect and save resident's profiles.")
        messenger_group.generate_group_json_list() # overwrite existing if there is one
        #add llm models later

        logger.info("Successfully retrieved admin access token and updated environment settings.")
    
    except Exception as e:
        # Log specific errors based on exception type
        logger.error(f"Error during setup: {e}")
        raise  # Re-raise exception after logging

    logger.info("FastAPI service setup complete.")


@bihua.get("/")
async def root():
    return {"message": "Welcome to Bihua service!"}



@bihua.post("/api/login", status_code=status.HTTP_200_OK)
async def admin_login(username: str = Body(..., embed=True), password: str = Body(..., embed=True)) -> Dict[str, str]:
    logger.info(f"Login attempt for username: {username}")

    try:
        # Attempt login using provided username and password
        login_status: LoginStatus = await bihua_api.admin_login(resident_id=username, password=password)

        if login_status == LoginStatus.SUCCESS:
            # Successful login
            logger.info(f"Login successful for username: {username}")
            return {
                "message": "Login successful",
                "status": f"{status.HTTP_200_OK}",
            }
        elif login_status == LoginStatus.ERROR:
            # Invalid credentials
            logger.warning(f"Invalid login attempt for username: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password. Please check your credentials and try again."
            )
        else:
            # If the status is EXCEPTION
            logger.error(f"Exception occurred during login for username: {username}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during the login process. Please try again later."
            )

    except HTTPException as e:
        # Re-raise known HTTPExceptions to handle them gracefully
        logger.error(f"HTTPException occurred: {str(e)}")
        raise e
    except Exception as e:
        # General exception handling
        logger.error(f"Unexpected error during login for username: {username} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@bihua.put("/api/register", status_code=status.HTTP_200_OK)
async def register_user(username: str = Body(..., embed=True), password: str = Body(..., embed=True)):
    logger.info(f"Registration attempt for username: {username}")

    try:
        # Call to register the user
        register: RegisterStatus = await bihua_api.register_user(username, password)

        # Check the result from the registration process
        if register == RegisterStatus.SUCCESS:
            logger.info(f"User registration successful for username: {username}")
            return {
                "message": "success",
                "status": str(status.HTTP_200_OK),
            }
        # Handle specific cases of failed registration
        elif register == RegisterStatus.INVALID_USERNAME:
            logger.warning(f"Invalid username during registration attempt for username: {username}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username.")
        elif register == RegisterStatus.NO_PERMISSION:
            logger.warning(f"No permission to register for username: {username}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to register.")
        elif register == RegisterStatus.USER_EXISTS:
            logger.warning(f"User already exists during registration attempt for username: {username}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")
        elif register == RegisterStatus.CREATION_FAILED:
            logger.error(f"User creation failed during registration attempt for username: {username}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed due to server error.")
        else:
            logger.error(f"Registration failed due to unknown reasons for username: {username}")
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Registration failed due to unknown reasons.")
    
    except HTTPException as e:
        # Catch known HTTP errors and re-raise them with appropriate details
        logger.error(f"HTTPException occurred during registration for username: {username} - {str(e)}")
        raise e
    except Exception as e:
        # For other unexpected errors, log them and return a generic internal error message
        logger.error(f"Unexpected error during registration for username: {username} - {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred. Please try again later.")


@bihua.put("/api/change", status_code=status.HTTP_200_OK)
async def change_user_settings(
    resident_id: str = Body(..., embed=True),
    display_name: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
    agent: str = Body(..., embed=True),
    role: str = Body(..., embed=True),
    state: str = Body(..., embed=True)
):
    try:
        if display_name is not None:
            logger.info(f"Attempting to change display name for resident_id={resident_id}")
            result: CheckCrudStatus = await bihua_api.change_user_display_name(resident_id, display_name)
            if result == CheckCrudStatus.SUCCESS:
                logger.info(f"Display name updated successfully for resident_id={resident_id}")
                return {"message": "success", "status": f"{status.HTTP_200_OK}"}
            elif result == CheckCrudStatus.NO_CHANGE:
                logger.info(f"No change in display name for resident_id={resident_id}")
            else:
                logger.error(f"Failed to update display name for resident_id={resident_id}, status: {result}")

        if password is not None:
            logger.info(f"Attempting to change password for resident_id={resident_id}")
            result: CheckCrudStatus = await bihua_api.change_user_password(resident_id, password)
            if result == CheckCrudStatus.SUCCESS:
                logger.info(f"Password updated successfully for resident_id={resident_id}")
                return {"message": "success", "status": f"{status.HTTP_200_OK}"}
            elif result == CheckCrudStatus.NO_CHANGE:
                logger.info(f"No change in password for resident_id={resident_id}")
            else:
                logger.error(f"Failed to update password for resident_id={resident_id}, status: {result}")

        if agent is not None:  # human or bot
            logger.info(f"Attempting to change agent type for resident_id={resident_id}")
            result: CheckCrudStatus = await bihua_api.change_user_type(resident_id, agent)
            if result == CheckCrudStatus.SUCCESS:
                logger.info(f"Agent type updated successfully for resident_id={resident_id}")
                return {"message": "success", "status": f"{status.HTTP_200_OK}"}
            elif result == CheckCrudStatus.NO_CHANGE:
                logger.info(f"No change in agent type for resident_id={resident_id}")
            else:
                logger.error(f"Failed to update agent type for resident_id={resident_id}, status: {result}")

        if role is not None:
            logger.info(f"Attempting to change role for resident_id={resident_id}")
            result: CheckCrudStatus = await bihua_api.change_user_role(resident_id, role)
            if result == CheckCrudStatus.SUCCESS:
                logger.info(f"Role updated successfully for resident_id={resident_id}")
                return {"message": "success", "status": f"{status.HTTP_200_OK}"}
            elif result == CheckCrudStatus.NO_CHANGE:
                logger.info(f"No change in role for resident_id={resident_id}")
            else:
                logger.error(f"Failed to update role for resident_id={resident_id}, status: {result}")

        if state is not None:
            logger.info(f"Attempting to change state for resident_id={resident_id}")
            result: CheckCrudStatus = await bihua_api.change_user_state(resident_id, state)
            if result == CheckCrudStatus.SUCCESS:
                logger.info(f"State updated successfully for resident_id={resident_id}")
                return {"message": "success", "status": f"{status.HTTP_200_OK}"}
            elif result == CheckCrudStatus.NO_CHANGE:
                logger.info(f"No change in state for resident_id={resident_id}")
            else:
                logger.error(f"Failed to update state for resident_id={resident_id}, status: {result}")

        # If no field is provided to update, raise an error
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="No valid field provided for update.")

    except HTTPException as http_err:
        logger.error(f"HTTPException occurred: {http_err.detail}")
        raise http_err  # Re-raise HTTPException to return it to the client
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")


@bihua.get("/api/resident_profile/{resident_id}", status_code=status.HTTP_200_OK)
async def resident_profile_get(resident_id: str) -> Dict[str, Any]:
    try:
        # Attempt to load the resident profile
        profile_status, profile_data = bihua_api.load_resident_profile(resident_id)

        # Check if the profile load was successful
        if profile_status == CrudStatus.SUCCESS:
            return_msg = {
                "message": "success",
                "status": f"{status.HTTP_200_OK}",
                "data": {
                    "description": profile_data
                }
            }
            logger.info(f"Successfully fetched profile for {resident_id}.")
            return return_msg

        # Handle case where profile is not found
        elif profile_status == CrudStatus.ERROR:
            error_msg = f"Profile not found for {resident_id}."
            logger.error(error_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

        # Handle unexpected error (exception case)
        elif profile_status == CrudStatus.EXCEPTION:
            error_msg = f"Unexpected error occurred while fetching profile for {resident_id}."
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        # Catch any unknown status
        else:
            error_msg = f"Unknown status {profile_status} while fetching profile for {resident_id}."
            logger.error(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    except HTTPException as e:
        # Log the HTTPException and re-raise it
        logger.error(f"HTTPException while fetching profile for {resident_id}: {e.detail}")
        raise e  # Re-raise the HTTPException to return the response correctly

    except Exception as e:
        # Log any unexpected errors
        logger.exception(f"Unexpected error while fetching profile for {resident_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@bihua.post("/api/resident_profile/{resident_id}/", status_code=status.HTTP_200_OK)
async def resident_profile_save(resident_id: str, profile_text: str = Body(..., embed=True)):
    try:
        # Attempt to save the resident profile
        profile_status, reason = bihua_api.save_resident_profile(resident_id, profile_text)

        # Handle successful profile save
        if profile_status == CrudStatus.SUCCESS:
            get_logger().info(f"Profile for {resident_id} successfully saved.")
            return {"message": "success", "status": f"{status.HTTP_200_OK}"}

        # Handle error during profile save
        elif profile_status == CrudStatus.ERROR:
            get_logger().error(f"Profile for {resident_id} not saved. Reason: {reason}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile not saved due to error.")

        # In case of unknown status
        else:
            get_logger().warning(f"Unknown status while saving profile for {resident_id}.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unknown error occurred.")

    except HTTPException as http_err:
        # Specific HTTPException handling (e.g., 404, 400, etc.)
        get_logger().error(f"HTTPException for {resident_id}: {http_err.detail}")
        raise http_err  # Re-raise the exception

    except Exception as e:
        # Log any unexpected errors
        get_logger().exception(f"Unexpected error while saving profile for {resident_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@bihua.get("/api/group_profile/{group_id}", status_code=status.HTTP_200_OK)
async def group_profile_get(group_id: str) -> Dict[str, Any]:
    try:
        # Attempt to load the group profile
        profile_status, profile_data = bihua_api.load_group_profile(group_id)

        # Check if the profile load was successful
        if profile_status == CrudStatus.SUCCESS:
            success_code = status.HTTP_200_OK
            return_msg = {
                "message": "success",
                "status": success_code,  # Direct status code (no string formatting)
                "data": {
                    "description": profile_data
                }
            }
            logger.info(f"Successfully fetched group profile for {group_id}.")
            return return_msg

        # Handle case where profile is not found
        elif profile_status == CrudStatus.ERROR:
            error_msg = f"Profile not found for {group_id}."
            logger.error(error_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

        # Handle unexpected error (exception case)
        elif profile_status == CrudStatus.EXCEPTION:
            error_msg = f"Unexpected error occurred while fetching group profile for {group_id}."
            logger.exception(error_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

        # Catch any unknown status
        else:
            error_msg = f"Unknown status {profile_status} while fetching group profile for {group_id}."
            logger.error(f"{error_msg} Status: {profile_status}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    except HTTPException as e:
        # Log the HTTPException and re-raise it
        logger.error(f"HTTPException while fetching profile for {group_id}: {e.detail}")
        raise e  # Re-raise the HTTPException to return the response correctly

    except Exception as e:
        # Log any unexpected errors with traceback for better debugging
        logger.exception(f"Unexpected error while fetching profile for {group_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")



@bihua.post("/api/group_profile/{group_id}/", status_code=status.HTTP_200_OK)
async def group_profile_save(group_id: str, profile_text: str = Body(..., embed=True)) -> Dict[str, Any]:
    try:
        # Attempt to save the group profile
        profile_status, reason = bihua_api.save_group_profile(group_id, profile_text)

        # Check if the profile was saved successfully
        if profile_status == CrudStatus.SUCCESS:
            success_code = status.HTTP_200_OK
            return_msg = {
                "message": "success",
                "status": success_code  # Direct status code, no need for string formatting
            }

            logger.info(f"Profile for {group_id} successfully saved.")
            return return_msg

        # Handle error during profile save (when status is ERROR)
        elif profile_status == CrudStatus.ERROR:
            error_msg = f"Profile for {group_id} not saved. Reason: {reason}"
            logger.error(error_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

        # Handle exception during profile save (when status is EXCEPTION)
        elif profile_status == CrudStatus.EXCEPTION:
            exception_msg = f"An exception occurred while saving profile for {group_id}. Reason: {reason}"
            logger.error(exception_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exception_msg)

        # In case of unknown status
        else:
            unknown_msg = f"Unknown status while saving profile for {group_id}."
            logger.warning(unknown_msg)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=unknown_msg)

    except HTTPException as http_err:
        # Specific HTTPException handling (e.g., 404, 400, etc.)
        logger.error(f"HTTPException for {group_id}: {http_err.detail}")
        raise http_err  # Re-raise the exception

    except Exception as e:
        # Log any unexpected errors with traceback for better debugging
        logger.exception(f"Unexpected error while saving profile for {group_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@bihua.delete("/api/resident_document_delete/{resident_id}/{file_name}", status_code=status.HTTP_200_OK)
async def document_delete(resident_id: str, file_name: str):
    try:
        # Log the start of the delete request
        logger.info(f"Received document delete request for resident_id: {resident_id}, file_name: {file_name}")

        # Perform the document delete operation
        delete_status, reason = bihua_api.delete_document(resident_id, file_name)
        
        # Handle different delete statuses
        if delete_status == CheckCrudStatus.SUCCESS:
            logger.info(f"Document {file_name} successfully deleted for resident {resident_id}.")
            return {
                "message": "success",
                "status": f"{status.HTTP_200_OK}",
            }

        elif delete_status == CheckCrudStatus.ERROR:
            logger.error(f"Failed to delete document {file_name} for resident {resident_id}. Reason: {reason}")
            return {
                "message": "error",
                "status": f"{status.HTTP_400_BAD_REQUEST}",
                "detail": reason
            }

        elif delete_status == CheckCrudStatus.EXCEPTION:
            logger.error(f"Exception occurred while deleting document {file_name} for resident {resident_id}.")
            return {
                "message": "exception",
                "status": f"{status.HTTP_500_INTERNAL_SERVER_ERROR}",
                "detail": reason
            }

        else:
            logger.warning(f"Unexpected status returned for document deletion: {delete_status}")
            return {
                "message": "unexpected_status",
                "status": f"{status.HTTP_500_INTERNAL_SERVER_ERROR}",
            }

    except Exception as e:
        # Log the exception and raise HTTPException
        logger.exception(f"An error occurred while deleting document {file_name} for resident {resident_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during document deletion.")
    

@bihua.delete("/api/group_document_delete/{group_id}/{file_name}", status_code=status.HTTP_200_OK)
async def document_delete(group_id: str, file_name: str):
    try:
        # Log the start of the delete request
        logger.info(f"Received document delete request for resident_id: {group_id}, file_name: {file_name}")

        # Perform the document delete operation
        delete_status, reason = bihua_api.delete_resident_document(group_id, file_name)
        
        # Handle different delete statuses
        if delete_status == CheckCrudStatus.SUCCESS:
            logger.info(f"Document {file_name} successfully deleted for resident {group_id}.")
            return {
                "message": "success",
                "status": f"{status.HTTP_200_OK}",
            }

        elif delete_status == CheckCrudStatus.ERROR:
            logger.error(f"Failed to delete document {file_name} for resident {group_id}. Reason: {reason}")
            return {
                "message": "error",
                "status": f"{status.HTTP_400_BAD_REQUEST}",
                "detail": reason
            }

        elif delete_status == CheckCrudStatus.EXCEPTION:
            logger.error(f"Exception occurred while deleting document {file_name} for resident {group_id}.")
            return {
                "message": "exception",
                "status": f"{status.HTTP_500_INTERNAL_SERVER_ERROR}",
                "detail": reason
            }

        else:
            logger.warning(f"Unexpected status returned for document deletion: {delete_status}")
            return {
                "message": "unexpected_status",
                "status": f"{status.HTTP_500_INTERNAL_SERVER_ERROR}",
            }

    except Exception as e:
        # Log the exception and raise HTTPException
        logger.exception(f"An error occurred while deleting document {file_name} for resident {group_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during document deletion.")
 

######################

@bihua.get("/api/documents/{id}", status_code=status.HTTP_200_OK)
async def get_document_list(id: str):
    try:
        logger.info(f"Received request to get document list for ID: {id}")
        
        if id.startswith("@"):
            resident_id = id
            logger.debug(f"Resident ID detected: {resident_id}")
            data_status, profile_data = bihua_api.get_uploaded_resident_document_names(resident_id)
        elif id.startswith("!"):
            group_id = id
            logger.debug(f"Group ID detected: {group_id}")
            data_status, profile_data = bihua_api.get_upladed_group_document_names(group_id)
        else:
            logger.error(f"Invalid ID format provided: {id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wrong ID is provided")

        if data_status == CheckCrudStatus.SUCCESS:
            success_code = status.HTTP_200_OK
            logger.info(f"Document data retrieval successful for ID: {id}")
            return_msg = {
                "message": "success",
                "status": f"{success_code}",
                "data": {
                    "document_tree": profile_data
                }
            }
            return return_msg
        else:
            logger.error(f"Failed to retrieve documents, status: {data_status} for ID: {id}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve documents")
    
    except Exception as e:
        logger.error(f"Error in get_document_list for ID: {id}, error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    

@bihua.post("/api/resident_avatar/{resident_id}", status_code=status.HTTP_200_OK)
async def upload_avatar(resident_id: str, file_to_be_upladed: UploadFile = File(...)):
    _resident = Resident(resident_id)
    temp_file_path = os.path.join(
        _resident.resident_star.star_residents_data_home,
        resident_id,
        _resident.resident_star.resident_document_subfolder
    )

    try:
        logger.info(f"Starting avatar upload for resident_id: {resident_id}, file: {file_to_be_upladed.filename}")
        
        # Save the uploaded file to the temp path
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file_to_be_upladed.read())
        logger.info(f"File saved temporarily at {temp_file_path}")

        # Call the function to update the avatar
        avatar_status = await bihua_api.update_user_avatar_in_messenger(resident_id, temp_file_path)
        logger.info(f"Avatar status for resident {resident_id}: {avatar_status}")

        # Clean up the temporary file after processing
        os.remove(temp_file_path)
        logger.info(f"Temporary file {temp_file_path} removed after processing.")

        if avatar_status == CrudStatus.SUCCESS:
            logger.info(f"Avatar update successful for resident {resident_id}")
            return_msg = {
                "message": "success",
                "status": f"{status.HTTP_200_OK}",
                "file": file_to_be_upladed.filename
            }
            return return_msg

        elif avatar_status == CrudStatus.ERROR:
            logger.error(f"Failed to update avatar for resident {resident_id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update avatar")
        
        else:
            logger.error(f"Unexpected error occurred while updating avatar for resident {resident_id}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")
    
    except Exception as e:
        # Clean up in case of any error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"Error occurred while uploading avatar for resident {resident_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error uploading avatar: {str(e)}")


@bihua.post("/api/group_avatar/{group_id}", status_code=status.HTTP_200_OK)
async def upload_avatar(group_id: str, file_to_be_upladed: UploadFile = File(...)):
    _group = Group(group_id)
    temp_file_path = os.path.join(
        _group.group_star.star_groups_data_home,
        group_id,
        _group.group_star.group_document_subfolder
    )

    try:
        logger.info(f"Starting avatar upload for resident_id: {group_id}, file: {file_to_be_upladed.filename}")
        
        # Save the uploaded file to the temp path
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file_to_be_upladed.read())
        logger.info(f"File saved temporarily at {temp_file_path}")

        # Call the function to update the avatar
        avatar_status = await bihua_api.update_group_avatar_in_messenger(group_id, temp_file_path)
        logger.info(f"Avatar status for resident {group_id}: {avatar_status}")

        # Clean up the temporary file after processing
        os.remove(temp_file_path)
        logger.info(f"Temporary file {temp_file_path} removed after processing.")

        if avatar_status == CrudStatus.SUCCESS:
            logger.info(f"Avatar update successful for group {group_id}")
            return_msg = {
                "message": "success",
                "status": f"{status.HTTP_200_OK}",
                "file": file_to_be_upladed.filename
            }
            return return_msg

        elif avatar_status == CrudStatus.ERROR:
            logger.error(f"Failed to update avatar for resident {group_id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update avatar")
        
        else:
            logger.error(f"Unexpected error occurred while updating avatar for group {group_id}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")
    
    except Exception as e:
        # Clean up in case of any error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"Error occurred while uploading avatar for group {group_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error uploading avatar: {str(e)}")


@bihua.post("/api/upload/{resident_id}", status_code=status.HTTP_200_OK)
async def upload_file(resident_id: str, file_to_be_upladed: UploadFile = File(...)):
    try:
        load_dotenv()
        HOME_PATH_OF_DATA_OF_EACH_RESIDENT = os.getenv("HOME_PATH_OF_DATA_OF_EACH_RESIDENT")
        DOCUMENTS_SUB_PATH = os.getenv("DOCUMENTS_SUB_PATH")
        document_folder = f"{HOME_PATH_OF_DATA_OF_EACH_RESIDENT}/{resident_id}/{DOCUMENTS_SUB_PATH}"
        file_destination_path = f"{document_folder}/{file_to_be_upladed.filename}"

        with open(file_destination_path, 'w+b') as file:
            shutil.copyfileobj(file_to_be_upladed.file, file)

        code=status.HTTP_200_OK
        renturn_msg = {
            "message": "success",
            "status": f"{code}",
            "file": file_to_be_upladed.filename
        }

        return renturn_msg

    except Exception as e:
        # await bihua_logging.bihua_logging(f"Error bihua_fastapi.upload_file: {e}", logging.ERROR)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@bihua.get("/api/residents/", status_code=status.HTTP_200_OK)
async def get_all_residents():
    try:
        logger.debug("point 0: Fetching all residents")
        messenger_resident.collect_and_save_residents_settings()
        list_status, resident_list_json = bihua_api.get_resident_list()

        if list_status == CrudStatus.SUCCESS:
            success_code = status.HTTP_200_OK
            return_msg = {
                "message": "success",
                "status": f"{success_code}",
                "data": {
                    "residents": resident_list_json
                }
            }
            logger.info(f"Fetched {len(resident_list_json)} residents successfully")
            return return_msg
        else:
            logger.warning("Failed to fetch residents: Unexpected status")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch residents")
    except Exception as e:
        logger.error(f"Error in get_all_residents: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@bihua.get("/api/groups/", status_code=status.HTTP_200_OK)
async def get_all_groups():
    try:
        logger.debug("point 0: Fetching all groups")
        messenger_group.collect_and_save_groups_settings()
        list_status, group_list_json = bihua_api.get_group_list()

        if list_status == CrudStatus.SUCCESS:
            success_code = status.HTTP_200_OK
            return_msg = {
                "message": "success",
                "status": f"{success_code}",
                "data": {
                    "groups": group_list_json
                }
            }
            logger.info(f"Fetched {len(group_list_json)} groups successfully")
            return return_msg
        else:
            logger.warning("Failed to fetch groups: Unexpected status")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch groups")
    except Exception as e:
        logger.error(f"Error in get_all_groups: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


sub_processes = []
import signal
# sudo pkill -f 'python3 bihua*'

@bihua.post("/start_clients", status_code=status.HTTP_200_OK)
async def start_clients():
    try:
        # Attempt to load the environment variables
        load_dotenv()
        
        # Get environment variables
        resident_id = os.getenv("ADMIN_ID")
        password = os.getenv("ADMIN_PASSWORD")
        access_token = os.getenv("ADMIN_ACCESS_TOKEN")
        
        # Check if the required environment variables are missing
        if not resident_id or not password or not access_token:
            logger.error("Missing one or more required environment variables.")
            return {"detail": "Missing required environment variables"}, status.HTTP_400_BAD_REQUEST

        # Log the start of the subprocess creation
        logger.info("Starting the resident_messenger_bot_service subprocess.")

        # Prepare the command to start the subprocess
        command = [
            "python3", "resident_messenger_bot_service.py",
            "--resident_id", resident_id,
            "--password", password,
            "--access_token", access_token
        ]

        # Start the subprocess
        p = subprocess.Popen(command)
        sub_processes.append(p)

        # Log the successful start
        logger.info(f"Started subprocess with PID {p.pid}.")

        # Return success response
        return {"message": "Clients started successfully."}, status.HTTP_200_OK

    except FileNotFoundError as fnf_error:
        logger.error(f"File not found error: {fnf_error}")
        return {"detail": f"File not found: {fnf_error}"}, status.HTTP_500_INTERNAL_SERVER_ERROR
    except subprocess.SubprocessError as subprocess_error:
        logger.error(f"Subprocess error: {subprocess_error}")
        return {"detail": f"Subprocess error: {subprocess_error}"}, status.HTTP_500_INTERNAL_SERVER_ERROR
    except Exception as e:
        # General exception catch
        logger.error(f"An unexpected error occurred: {e}")
        return {"detail": "An unexpected error occurred"}, status.HTTP_500_INTERNAL_SERVER_ERROR
    
@bihua.post("/start_clients", status_code=status.HTTP_200_OK)
async def start_clients():
    try:
        load_dotenv()
        resident_id = os.getenv("ADMIN_ID")
        password = os.getenv("ADMIN_PASSWORD")
        access_token = os.getenv("ADMIN_ACCESS_TOKEN")

        command = ["python3", "resident_messenger_bot_service.py", "--resident_id", resident_id, "--password", password, "--access_token", access_token]
        p = subprocess.Popen(command)
        sub_processes.append(p)
    except Exception as e:
        return False

        # load_dotenv()
        # STAR_RESIDENT_LIST_JSON_PATH = os.getenv("STAR_RESIDENT_LIST_JSON_PATH")
        # STAR_SERVER_SYNAPSE_URL = os.getenv("STAR_SERVER_SYNAPSE_URL")
        # print(STAR_SERVER_SYNAPSE_URL)

        # with open(STAR_RESIDENT_LIST_JSON_PATH, 'r') as file:
        #     resident_list_json = json.load(file)

        # for item in resident_list_json:
        #     if item["agent"] == "disabled":
        #         continue
        #     resident_id = item["resident_id"]
        #     password = item["password"]
        #     access_token = item["access_token"]

        #     # command = f"python3 bihua_run_one_resident.py --resident_id {resident_id} --password {password} --email {email} --llm {llm}"

        #     command = ["python3", "resident_messenger_bot_service.py", "--resident_id", resident_id, "--password", password, "--access_token", access_token]
        #     print(f"command = {command}")

        #     p = subprocess.Popen(command)
        #     sub_processes.append(p)
            
        # return True

    # except Exception as e:
    #     # await bihua_logging.bihua_logging(f"Error bihua_fastapi.start_clients_endpoint: {e}", logging.ERROR)
    #     return False

    
@bihua.post("/stop_clients", status_code=status.HTTP_200_OK)
async def stop_clients():
    global sub_processes
    try:
        for p in sub_processes:
            print(f"stop_clients.p.pid = {p.pid}")
            os.kill(int(p.pid), signal.SIGINT)
            p.wait()  # Wait for the process to terminate
        sub_processes = []
        return True

    except Exception as e:
        # await bihua_logging.bihua_logging(f"Error bihua_fastapi.stop_clients_endpoint: {e}", logging.ERROR)
        return False

############################################################################################
@bihua.get("/api/llm_model_list/", status_code=status.HTTP_200_OK)
async def get_llm_model_list():
    list_status, data = bihua_api.get_llm_model_list()
    if list_status == CrudStatus.SUCCESS:
            success_code = status.HTTP_200_OK
            return_msg = {
                "message": "success",
                "status": f"{success_code}",
                "data": {
                    "llm_model_list": data
                }
            }
            logger.info(f"Fetched {len(data)} residents successfully")
            return return_msg

@bihua.get("/api/llm_model/{llm_model_id}", status_code=status.HTTP_200_OK)
async def get_llm_model_list(llm_model_id):
    model_status, data = bihua_api.fetch_llm_model_by_id(llm_model_id)
    if model_status == CrudStatus.SUCCESS:
            success_code = status.HTTP_200_OK
            return_msg = {
                "message": "success",
                "status": f"{success_code}",
                "data": {
                    "model_details": data
                }
            }
            logger.info(f"Fetched {len(data)} residents successfully")
            return return_msg


# @bihua.put("/api/chat", status_code=status.HTTP_200_OK)
# async def api_chat(
#     resident_id: Optional[str] = Body(None, embed=True), 
#     password: Optional[str] = Body(None, embed=True),
#     access_token: Optional[str] = Body(None, embed=True),
#     room_id: Optional[str] = Body(None, embed=True),
#     msg_receivers: Optional[list] = Body(None, embed=True),
#     message: Optional[str] = Body(None, embed=True),
#     text_files: Optional[list] = Body(None, embed=True),
#     images: Optional[list] = Body(None, embed=True),
#     audios: Optional[list] = Body(None, embed=True),
#     videos: Optional[list] = Body(None, embed=True)
# ):
#     pass

# API Endpoints：

# /api/login：管理员登录接口。
# /api/register：用户注册接口。
# /api/change：更改用户设置的接口。
# /api/resident_profile/{resident_id}：获取居民（用户）资料的接口。
# /api/resident_profile/{resident_id}/：保存居民资料的接口。
# /api/group_profile/{group_id}：获取群组资料的接口。
# /api/group_profile/{group_id}/：保存群组资料的接口。
# /api/resident_document_delete/{resident_id}/{file_name}：删除居民文件的接口。
# /api/group_document_delete/{group_id}/{file_name}：删除群组文件的接口。
# /api/documents/{id}：获取文档列表的接口。
# /api/resident_avatar/{resident_id}：上传居民头像的接口。
# /api/group_avatar/{group_id}：上传群组头像的接口。
# /api/upload/{resident_id}：上传文件的接口。
# /api/residents/：获取所有居民列表的接口。
# /api/groups/：获取所有群组列表的接口。
# /start_clients：启动客户端服务的接口。
# /stop_clients：停止客户端服务的接口。
# /api/llm_model_list/：获取大型语言模型列表的接口。
# /api/llm_model/{llm_model_id}：根据 ID 获取大型语言模型详情的接口。
