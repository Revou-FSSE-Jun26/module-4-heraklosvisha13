from marshmallow import Schema, fields


class ColumnCountSchema(Schema):
    column_id = fields.String()
    name = fields.String()
    count = fields.Integer()


class CompletedThisWeekSchema(Schema):
    count = fields.Integer()
    week_start = fields.String()


class MemberActivitySchema(Schema):
    user_id = fields.String()
    name = fields.String()
    assigned_count = fields.Integer()
    completed_this_week = fields.Integer()
    comments_count = fields.Integer()


class AnalyticsSchema(Schema):
    cards_per_column = fields.List(fields.Nested(ColumnCountSchema))
    completed_this_week = fields.Nested(CompletedThisWeekSchema)
    member_activity = fields.List(fields.Nested(MemberActivitySchema))
