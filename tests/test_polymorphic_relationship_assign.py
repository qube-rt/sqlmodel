from typing import Optional

from sqlmodel import Field, Relationship, Session, SQLModel, create_engine


def _make_owner_tool_classes():
    """Owner → Tool (base) → Hammer (joined table inheritance subclass)."""

    class Owner(SQLModel, table=True):
        __tablename__ = "owner"
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str
        tools: list["Tool"] = Relationship(back_populates="owner")

    class Tool(SQLModel, table=True):
        __tablename__ = "tool"
        id: Optional[int] = Field(default=None, primary_key=True)
        type: str = Field(default="tool")
        owner_id: Optional[int] = Field(default=None, foreign_key="owner.id")
        owner: Optional[Owner] = Relationship(back_populates="tools")

        __mapper_args__ = {
            "polymorphic_on": "type",
            "polymorphic_identity": "tool",
        }

    class Hammer(Tool, table=True):
        __tablename__ = "hammer"
        id: Optional[int] = Field(
            default=None, primary_key=True, foreign_key="tool.id"
        )
        weight: Optional[float] = Field(default=None)

        __mapper_args__ = {"polymorphic_identity": "hammer"}

    return Owner, Tool, Hammer



def _make_node_classes():
    """For self-referential tests"""
    class BaseNode(SQLModel, table=True):
        __tablename__ = "basenode"
        id: str = Field(primary_key=True)
        node_type: str = Field(default="base")
        next_id: Optional[str] = Field(
            default=None, foreign_key="basenode.id"
        )
        next: Optional["BaseNode"] = Relationship(
            sa_relationship_kwargs={"remote_side": "BaseNode.id", "uselist": False}
        )

        __mapper_args__ = {
            "polymorphic_on": "node_type",
            "polymorphic_identity": "base",
        }

    class EmailNode(BaseNode):
        __mapper_args__ = {"polymorphic_identity": "email"}

    return BaseNode, EmailNode



def test_setattr_inherited_relationship():
    """Assigning an inherited relationship on a joined table inheritance subclass should work."""
    Owner, Tool, Hammer = _make_owner_tool_classes()
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        bob = Owner(name="Bob")
        db.add(bob)
        db.flush()

        h = Hammer(weight=1.5)
        db.add(h)
        db.flush()

        h.owner = bob

        db.commit()
        h_id = h.id

    with Session(engine) as db:
        h = db.get(Hammer, h_id)
        assert h.owner_id is not None
        assert h.owner.name == "Bob"


def test_setattr_inherited_relationship_updates_fk():
    """Re-assigning the inherited relationship updates the foreign key on flush/commit."""
    Owner, Tool, Hammer = _make_owner_tool_classes()
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        alice = Owner(name="Alice")
        bob = Owner(name="Bob")
        db.add_all([alice, bob])
        db.flush()
        alice_id, bob_id = alice.id, bob.id

        h = Hammer(weight=2.0)
        db.add(h)
        db.flush()

        h.owner = alice
        db.flush()
        assert h.owner_id == alice_id

        h.owner = bob
        db.commit()

    with Session(engine) as db:
        h = db.get(Hammer, 1)
        assert h.owner_id == bob_id


def test_sti_self_referential_chain():
    """A chain of self-referential single table inheritance nodes persists and reloads correctly."""
    BaseNode, EmailNode = _make_node_classes()
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        a = EmailNode(id="a")
        b = EmailNode(id="b")
        c = EmailNode(id="c")
        db.add_all([a, b, c])
        db.flush()

        a.next = b
        b.next = c

        db.commit()

    with Session(engine) as db:
        a = db.get(BaseNode, "a")
        assert isinstance(a, EmailNode)
        assert a.next.id == "b"
        assert a.next.next.id == "c"


