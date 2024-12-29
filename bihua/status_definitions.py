from enum import Enum

class RegisterStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    INVALID_USERNAME = "invalid_username"
    NO_PERMISSION = "no_permission"
    USER_EXISTS = "user_exists"
    CREATION_FAILED = "creation_failed"
    EXCEPTION = "exception"

class CheckCrudStatus(Enum):
    SUCCESS = "success"
    NO_CHANGE = "new value and old value are the same. no need to update"
    ERROR = "error"
    EXCEPTION = "exception"

class CrudStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    EXCEPTION = "exception"

class LoginStatus(Enum):
    SUCCESS = "success"
    ERROR = "user id or password is not correct"
    EXCEPTION = "unexpected exception"

class AgentStatus(Enum):
    SUCCESS = "Success"
    ERROR = "Error in agent credentials or internal server issue"
    EXCEPTION = "Unexpected exception occurred"


