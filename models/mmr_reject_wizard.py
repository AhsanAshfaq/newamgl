# -*- coding: utf-8 -*-

import re

from odoo import models, fields
from odoo.exceptions import ValidationError


class RejectWizard(models.TransientModel):
    _name = 'amgl.reject_wizard'

    name = fields.Html(string="Rejection Reason", required=True)
    mmr_id = fields.Many2one('amgl.metal_movement', string='MMR Id')

    def get_additional_email_subject_info(self):
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        subject = ''
        if 'irastorage' not in base_url:
            if 'localhost' in base_url:
                subject = '(Test: Localhost) '
            elif 'odev' in base_url:
                subject = '(Test: Odev) '
        return subject

    def get_users_for_email(self,user_groups):
        users_for_email = []
        for group in user_groups:
            self.env.cr.execute(
                "select * from res_users where id in (select uid from res_groups_users_rel where gid in (select id from res_groups where name = '" + str(group) + "' ))")
            users = self.env.cr.fetchall()
            if users:
                for user in users:
                    users_for_email.append(user)
        return users_for_email

    def update_reject1(self):
        if self._context['active_id']:
            mmr_id = self._context['active_id']
            mmr_object = self.env['amgl.metal_movement'].search([('id', '=', mmr_id)])

            if mmr_object.state == 'completed':
                raise ValidationError('This particular withdrawal is in completed state, you cannot reject it.')

            if (self.env.user == mmr_object.first_approve and mmr_object.is_first_approve) or (self.env.user == mmr_object.second_approve and mmr_object.is_second_approve):
                raise ValidationError('You have already approved the particular withdrawal!')

            if mmr_object.is_rejected:
                raise ValidationError('This particular withdrawal is already rejected, please wait untill its gets revised.')

            else:
                self.env.cr.execute(
                "UPDATE amgl_metal_movement SET is_first_approve = FALSE , is_second_approve = FALSE, state = 'rejected', rejection_reason=%s , is_rejected=TRUE WHERE id=%s",
                    [self.name, mmr_id])
                base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
                mmr_menu = self.env['ir.ui.menu'].search([('name', '=', 'Withdrawal')])
                mmr_windows_action = self.env['ir.actions.act_window'].search([('res_model', '=', 'amgl.metal_movement')], limit=1)
                temp_mmr_link = base_url + "/web#id=" + str(mmr_id) + "&view_type=form&model=amgl.metal_movement&action=" + str(mmr_windows_action.id) +"&menu_id=" + str(mmr_menu.id)
                # send email to metal movement request creater
                creator_email_id = self.env['res.users'].search([('id', '=', mmr_object.create_uid.id)]).email
                email_list = str(creator_email_id)
                # removing html tags
                p = re.compile(r'<.*?>')
                reason_text = p.sub('', self.name)
                template = self.env.ref('amgl.reject_mmr_email', raise_if_not_found=True)
                additional_email_subject_info = self.get_additional_email_subject_info()
                user_groups = ['Administrator', 'Sub-Admins']
                user_for_email = self.get_users_for_email(user_groups)
                email_cc = self.env['ir.config_parameter'].get_param('email.cc')
                for user_email in user_for_email:
                    mail_id = template.with_context(rejected_by=str(self.env.user.name), email=email_list,
                                                    additional_email_subject=str(additional_email_subject_info),
                                                    reason=reason_text,mmr_link = temp_mmr_link,
                                                    email_cc = email_cc).send_mail(
                        user_email[0], force_send=False, raise_exception=True
                    )
        base_url = self.env['ir.config_parameter'].get_param('amgl.live.url')
        return {
                'type': 'ir.actions.act_url',
                'url': str(base_url) + '/amgl/static/html/rejection_accpeted.html',
                'target': 'self'
                }
