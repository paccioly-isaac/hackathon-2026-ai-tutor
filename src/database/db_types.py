"""Database types for MongoDB document schemas.

These models represent the structure of documents stored in MongoDB collections.
"""

from pydantic import BaseModel, Field


##INPUT TYPES##

def vector_search(
    client: MongoClient,
    database_name: str,
    collection_name: str,
    search_query: str,
    embedder: Embedder,
    vector_field_path: str,
    vector_index_name: str,
    top_k: int,
    num_candidates: int | None = None,
    filter: dict[str, Any] | None = None,

class ContentInput(BaseModel):
    
    database_name: str = "educational-content",
    collection_name: str = "page_vector",
    vector_field_path: str = "summary_vector",
    vector_index_name: str = "summary_vector_index"

class QuestionInput(BaseModel):
    
    database_name: str = "question-manager-v3",
    collection_name: str = "SAS",
    vector_field_path: str = "vector",
    vector_index_name: str = "SAS-vectordb"


##OUTPUT TYPES##
class ObjectId(BaseModel):
    """MongoDB ObjectId representation."""

    oid: str = Field(..., alias="$oid", description="MongoDB ObjectId string")

    class Config:
        populate_by_name = True


class ContentOutput(BaseModel):
    """Content document retrieved from MongoDB."""

    id: ObjectId = Field(..., alias="_id", description="Document ObjectId")
    image_ref: list[ObjectId] = Field(
        default_factory=list, description="List of image reference ObjectIds"
    )
    text: str = Field(..., description="Content text in markdown format")

    class Config:
        populate_by_name = True


class QuestionOption(BaseModel):
    """A single option for a multiple-choice question."""

    id: int = Field(..., description="Option unique identifier")
    order: int = Field(..., description="Display order of the option")
    text: str = Field(..., description="Option text (HTML formatted)")
    is_correct: bool = Field(..., alias="isCorrect", description="Whether this is the correct answer")
    commentary: str | None = Field(None, description="Optional commentary for the option")

    class Config:
        populate_by_name = True


class QuestionOutput(BaseModel):
    """Question document retrieved from MongoDB."""

    question_id: int = Field(..., alias="questionId", description="Question unique identifier")
    text: str = Field(..., description="Question text (HTML formatted)")
    options: list[QuestionOption] = Field(..., description="List of answer options")
    resolution: str = Field(..., description="Explanation/resolution of the question (HTML formatted)")

    class Config:
        populate_by_name = True
