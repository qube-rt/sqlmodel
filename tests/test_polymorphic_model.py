from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlmodel import Field, Session, SQLModel, create_engine, select


def test_polymorphic_joined_table(clear_sqlmodel) -> None:
    class Hero(SQLModel, table=True):
        __tablename__ = "hero"
        id: Optional[int] = Field(default=None, primary_key=True)
        hero_type: str = Field(default="hero")

        __mapper_args__ = {
            "polymorphic_on": "hero_type",
            "polymorphic_identity": "normal_hero",
        }

    class DarkHero(Hero):
        __tablename__ = "dark_hero"
        id: Optional[int] = Field(
            default=None,
            sa_column=mapped_column(ForeignKey("hero.id"), primary_key=True),
        )
        dark_power: str = Field(
            default="dark",
            sa_column=mapped_column(
                nullable=False, use_existing_column=True, default="dark"
            ),
        )

        __mapper_args__ = {
            "polymorphic_identity": "dark",
        }

    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        hero = Hero()
        db.add(hero)
        dark_hero = DarkHero()
        db.add(dark_hero)
        db.commit()

        result = db.exec(select(DarkHero)).all()
        assert len(result) == 1
        assert result[0].hero_type == "dark"
        assert isinstance(result[0].dark_power, str)
