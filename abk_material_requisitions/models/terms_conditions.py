
from odoo import api, fields, models


class TermsConditions(models.Model):
    _name = 'abk.terms.conditions'
    _description = 'Terms and Conditions'
    _rec_name = 'name'
    _order = "sequence, name, id"

    name = fields.Char(string="Name")
    description = fields.Text(string="Description")
    sequence = fields.Integer('Sequence', default=1, help="Used to order stages. Lower is better.")
