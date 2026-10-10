from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

SUBJECT_MAX_LENGTH = 200
BODY_MAX_LENGTH = 10_000


class SendEmailRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    to: EmailStr
    subject: str = Field(min_length=1, max_length=SUBJECT_MAX_LENGTH)
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)

    @field_validator("subject")
    @classmethod
    def subject_single_line(cls, value: str) -> str:
        # Prevents email header injection.
        if "\r" in value or "\n" in value:
            raise ValueError("Subject must not contain line breaks")
        return value


class SendEmailResponse(BaseModel):
    success: bool
    message: str


class HealthResponse(BaseModel):
    status: str
