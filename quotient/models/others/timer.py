from tortoise import fields

from quotient.models import BaseDbModel


class Timer(BaseDbModel):
    class Meta:
        table = "timers"

    id = fields.BigIntField(primary_key=True)
    expires = fields.DatetimeField(db_index=True)
    created = fields.DatetimeField(auto_now_add=True)
    event = fields.CharField(max_length=100)
    extra = fields.JSONField(default=dict)

    @property
    def kwargs(self):
        return self.extra.get("kwargs", {})

    @property
    def args(self):
        return self.extra.get("args", ())
