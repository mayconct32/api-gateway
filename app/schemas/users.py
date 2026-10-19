from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload de cadastro público de usuário."""

    full_name: str = Field(min_length=3, max_length=100)
    email: EmailStr
    # Senha com complexidade mínima; o valor nunca retorna na resposta.
    password: str = Field(min_length=8, max_length=64)


class UserRead(BaseModel):
    """Usuário devolvido nas respostas, sem expor a senha."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str


class UserUpdate(BaseModel):
    """Payload de atualização parcial; campos ausentes não são alterados."""

    full_name: str | None = Field(default=None, min_length=3, max_length=100)
    email: EmailStr | None = None
