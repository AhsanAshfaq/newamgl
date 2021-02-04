function join_name(names) {
    var str = "";
    var step;
    for (step = 0; step < names.length; step++) {
        str = str + (step + 1) + '- ' + names[step].full_name + ' \n';
    };
    return str;
}
function add_oz_with_weights(){
    sections = $('.oe_subtotal_footer');
	  for(i=0; i < sections.length; i++){
	    if(i == 1 || i == 3)
	        continue;
	    else{
	            spans = $($('.oe_subtotal_footer')[i]).find('tbody').find('tr').find('span')
	            for(j=0;j<spans.length;j++)
	            {
	                current_text = $(spans[j]).text();
	                if(current_text.indexOf('oz') > -1)
	                    continue
	                else
	                    $(spans[j]).text( current_text + ' oz')
	            }
	        }
	  }
}
$(function(){

    $(document).arrive("*[data-field='administrative_fees']", function() {
        admin_fees = $("*[data-field='administrative_fees']").find('p')
        for(i=0; i < admin_fees.length;i++){
             if ($($("*[data-field='administrative_fees']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='administrative_fees']").find('p')[i]).text('$'+ $($("*[data-field='administrative_fees']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
         }
         shipment_fees = $("*[data-field='shipment_fees']").find('p')
        for(i=0; i < shipment_fees.length;i++){
             if ($($("*[data-field='shipment_fees']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='shipment_fees']").find('p')[i]).text('$'+ $($("*[data-field='shipment_fees']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
         }
         outbound_fees = $("*[data-field='outbound_fees']").find('p')
        for(i=0; i < admin_fees.length;i++){
             if ($($("*[data-field='outbound_fees']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='outbound_fees']").find('p')[i]).text('$'+ $($("*[data-field='outbound_fees']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
         }
         total_fees = $("*[data-field='total_fees']").find('p')
        for(i=0; i < total_fees.length;i++){
             if ($($("*[data-field='total_fees']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='total_fees']").find('p')[i]).text('$'+ $($("*[data-field='total_fees']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
        }
        other_fees = $("*[data-field='other_fees']").find('p')
        for(i=0; i < total_fees.length;i++){
            if ($($("*[data-field='other_fees']").find('p')[i]).text().indexOf('$') == -1)
            {
               $($("*[data-field='other_fees']").find('p')[i]).text('$'+ $($("*[data-field='other_fees']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
            }
         }
	});
	$(document).arrive("*[data-field='gold_rate']", function() {
         gold_rate = $("*[data-field='gold_rate']").find('p')
         for(i=0; i < gold_rate.length;i++){
             if ($($("*[data-field='gold_rate']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='gold_rate']").find('p')[i]).text('$'+ $($("*[data-field='gold_rate']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
         }
         silver_rate = $("*[data-field='silver_rate']").find('p')
         for(i=0; i < silver_rate.length;i++){
             if ($($("*[data-field='silver_rate']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='silver_rate']").find('p')[i]).text('$'+ $($("*[data-field='silver_rate']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
         }
         platinum_rate = $("*[data-field='platinum_rate']").find('p')
         for(i=0; i < platinum_rate.length;i++){
             if ($($("*[data-field='platinum_rate']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='platinum_rate']").find('p')[i]).text('$'+ $($("*[data-field='platinum_rate']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
         }
         palladium_rate = $("*[data-field='palladium_rate']").find('p')
         for(i=0; i < palladium_rate.length;i++){
             if ($($("*[data-field='palladium_rate']").find('p')[i]).text().indexOf('$') == -1)
             {
                $($("*[data-field='palladium_rate']").find('p')[i]).text('$'+ $($("*[data-field='palladium_rate']").find('p')[i]).text().replace(/[\n\r]+/g, '').replace(/ /g,''))
             }
         }

	});
	$(document).arrive(".o_import_compat",function(){
	    if ($('.o_import_compat').children().length == 2){
            $($('.o_import_compat').children()[1]).remove();
        }
	});
	$(document).arrive("*[data-field='first_name']", function() {
	    $('table').css('white-space','nowrap');
	    all_row_paragraphs = $('table').find('tbody').find('.o_list_number p');
	    for(i=0;i<all_row_paragraphs.length;i++)
	    {
	        if (!(i%2 == 0)){
	            current_text = $(all_row_paragraphs[i]).text()
	            if(current_text.indexOf('$') > -1)
                    continue;
                else{

                    text = '$' + current_text.replace(/[\n\r]+/g, '')
                    $(all_row_paragraphs[i]).text(text);
                    continue;
                }

	        }
	        else{
                current_text = $(all_row_paragraphs[i]).text()
                if(current_text.indexOf('oz') > -1)
                    continue;
                else
                    $(all_row_paragraphs[i]).text(current_text.replace(/[\n\r]+/g, '') + ' oz');
	        }
	    }
		$('table').addClass('ei-table');
		add_oz_with_weights();
	});
	$(document).arrive(".oe_subtotal_footer", function() {
	  add_oz_with_weights();
	});
	$(document).arrive("*[data-field='commodity']", function() {
	    $("*[data-field='commodity']").parent().parent().parent().addClass('ei-table');
//	    $('.o_list_view').addClass('ei-table');
	    $('*[data-field="quantity"]').addClass('right-align');
	    $('*[data-id="quantity"]').addClass('right-align');
	    $('*[data-field="total_weight"]').addClass('right-align');
	    $('*[data-id="total_weight"]').addClass('right-align');
	    $('*[data-field="remaining_quantity"]').addClass('right-align');
	    $('*[data-id="remaining_quantity"]').addClass('right-align');
	    $('*[data-field="total_received_quantity"]').addClass('right-align');
	    $('*[data-id="total_received_quantity"]').addClass('right-align');
	    $('*[data-field="remaining_weight"]').addClass('right-align');
	    $('*[data-id="remaining_weight"]').addClass('right-align');
	    $('*[data-field="temp_received_weight"]').addClass('right-align');
	    $('*[data-id="temp_received_weight"]').addClass('right-align');
	    $('*[data-id="temp_received_weight"]').width('140px');
	    add_oz_with_weights();
	});
});
odoo.define('amgl.web.ListView', function (require) {
    "use strict";
    var core = require('web.core');
    var _t = core._t;
    var Model = require('web.DataModel');
	var utils = require('web.utils');


	var Editor = require('web.ListEditor')
	var list_editable_view = require('web.ListView')
    var ListView = core.view_registry.get('list');

    list_editable_view.include({
        init: function () {
        var self = this;
        this._super.apply(this, arguments);

        this.saving_mutex = new utils.Mutex();

        this._force_editability = null;
        this._context_editable = false;
        this.editor = new Editor(this);
        // Stores records of {field, cell}, allows for re-rendering fields
        // depending on cell state during and after resize events
        this.fields_for_resize = [];
        core.bus.on('resize', this, this.resize_fields);

        $(this.groups).bind({
            'edit': function (e, id, dataset) {
                self.do_edit(dataset.index, id, dataset);
            },
            'saved': function () {
                if (self.groups.get_selection().length) {
                    return;
                }
                self.configure_pager(self.dataset);
                self.compute_aggregates();
            }
        });

        this.records.bind('remove', function () {
            if (self.editor.is_editing()) {
                self.cancel_edition();
            }
        });

        this.on('edit:before', this, function (event) {
            if (!self.editable() || self.editor.is_editing()) {
                event.cancel = true;
            }
        });
        this.on('edit:after', this, function () {
            self.$el.add(self.$buttons).addClass('o-editing');
            self.$('.ui-sortable').sortable('disable');
        });
        this.on('save:after cancel:after', this, function () {
            self.$('.ui-sortable').sortable('enable');
            self.$el.add(self.$buttons).removeClass('o-editing');
            // Following lines are to change one2many row color which is currently created but page is not saved yet in order that user can separate them.
            var new_rows = $('*[data-id*=one2many]:visible');
            for (var index = 0; index < new_rows.length; ++index) {
               $(new_rows[index]).children('td, th').css('color','#008FB2');
            }
        });
    },
    });

    ListView.List.include({
        row_clicked: function (e, view) {
            if( this.view.is_action_enabled('open') )
                this._super.apply(this, arguments);
        },
    });

    ListView.include({
        render_buttons: function(){
            this._super.apply(this, arguments)
            if(this.$buttons){
                this.$buttons.find('.new_account_billing_commingled').on('click',function(){
                    new Model('amgl.customer').call('print_report_new_accounts_billing', [[]])
                })
                this.$buttons.find('.new_account_billing_commingled').on('click',function(){
                    new Model('amgl.customer').call('print_report_new_accounts_billing', [[]])
                })
            }
        },
        do_load_state: function (state, warm) {
            var reload = false;
            if (state.min && this.current_min !== state.min) {
                this.current_min = state.min;
                reload = true;
            }
            if (state.limit) {
                if (_.isString(state.limit)) {
                    state.limit = null;
                }
                if (state.limit !== this._limit) {
                    this._limit = state.limit;
                    reload = true;
                }
            }
            if (reload) {
                this.reload_content();
            }
        },
        do_delete: function (ids) {
            if (this.model == 'amgl.customer') {
                var self = this;
                new Model(self.model).call('read', [ids, ['full_name'], this.dataset.get_context()])
                .done(function (names) {
                    var text = _t("Do you really want to remove these records?") + ' \n \n' + join_name(names)
                    if (!(ids.length && confirm(text))) {
                        return;
                    }
                    return $.when(self.dataset.unlink(ids)).done(function () {
                        _(ids).each(function (id) {
                            self.records.remove(self.records.get(id));
                        });
                        if (self.display_nocontent_helper()) {
                            self.no_result();
                        } else {
                            if (self.records.length && self.current_min === 1) {
                                self.reload();
                            } else if (self.records.length && self.dataset.size() > 0) {
                                self.pager.previous();
                            }
                            if (self.current_min + self._limit - 1 < self.dataset.size()) {
                                self.reload();
                            }
                        }
                        self.update_pager(self.dataset);
                        self.compute_aggregates();
                    });
                });
            }
            else {
                if (!(ids.length && confirm(_t("Do you really want to remove these records?")))) {
                    return;
                }
                var self = this;
                return $.when(this.dataset.unlink(ids)).done(function () {
                    _(ids).each(function (id) {
                        self.records.remove(self.records.get(id));
                    });
                    if (self.display_nocontent_helper()) {
                        self.no_result();
                    } else {
                        if (self.records.length && self.current_min === 1) {
                            self.reload();
                        } else if (self.records.length && self.dataset.size() > 0) {
                            self.pager.previous();
                        }
                        if (self.current_min + self._limit - 1 < self.dataset.size()) {
                            self.reload();
                        }
                    }
                    self.update_pager(self.dataset);
                    self.compute_aggregates();
                });
            }
        },
        format: function (row_data, options) {
            res = this._super.apply(this, arguments);
            console.log(res);
            return res
        }
    });
	function synchronized(fn) {
    var fn_mutex = new utils.Mutex();
    return function () {
        add_oz_with_weights();
        var obj = this;
        var args = _.toArray(arguments);
        return fn_mutex.exec(function () {
            if (obj.isDestroyed()) { return $.when(); }
            return fn.apply(obj, args);
        });
		};
	}
});
odoo.define('amgl.web.FormView', function (require) {
    "use strict";
    var core = require('web.core');
    var _t = core._t;
    var Model = require('web.DataModel');
	var utils = require('web.utils');
    var FormView = core.view_registry.get('form');
    var Sidebar = require('web.Sidebar');
    FormView.include({
    _process_save: function(save_obj) {
        add_oz_with_weights();
        var self = this;
        var prepend_on_create = save_obj.prepend_on_create;
        var def_process_save = $.Deferred();
        try {
            var form_invalid = false,
                values = {},
                first_invalid_field = null,
                readonly_values = {},
                deferred = [];

            $.when.apply($, deferred).always(function () {

                _.each(self.fields, function (f) {
                    if (!f.is_valid()) {
                        form_invalid = true;
                        if (!first_invalid_field) {
                            first_invalid_field = f;
                        }
                    } else if (f.name !== 'id' && (!self.datarecord.id || f._dirty_flag)) {
                        // Special case 'id' field, do not save this field
                        // on 'create' : save all non readonly fields
                        // on 'edit' : save non readonly modified fields
                        if (!f.get("readonly")) {
                            values[f.name] = f.get_value(true);
                        } else {
                            readonly_values[f.name] = f.get_value(true);
                        }
                    }

                });

                // Heuristic to assign a proper sequence number for new records that
                // are added in a dataset containing other lines with existing sequence numbers
                if (!self.datarecord.id && self.fields.sequence &&
                    !_.has(values, 'sequence') && !_.isEmpty(self.dataset.cache)) {
                    // Find current max or min sequence (editable top/bottom)
                    var current = _[prepend_on_create ? "min" : "max"](
                        _.map(self.dataset.cache, function(o){return o.values.sequence})
                    );
                    values['sequence'] = prepend_on_create ? current - 1 : current + 1;
                }
                if (form_invalid) {
                    self.set({'display_invalid_fields': true});
                    first_invalid_field.focus();
                    self.on_invalid();
                    def_process_save.reject();
                } else {
                    self.set({'display_invalid_fields': false});
                    var save_deferral;
                    if (!self.datarecord.id) {
                        // Creation save
                        save_deferral = self.dataset.create(values, {readonly_fields: readonly_values}).then(function(r) {
                            self.display_translation_alert(values);
                            return self.record_created(r, prepend_on_create);
                        }, null);
                    } else if (_.isEmpty(values)) {
                        // Not dirty, noop save
                        save_deferral = $.Deferred().resolve({}).promise();
                    } else {
                        // Write save
                        save_deferral = self.dataset.write(self.datarecord.id, values, {readonly_fields: readonly_values}).then(function(r) {
                            self.display_translation_alert(values);
                            return self.record_saved(r);
                        }, null);
                    }
                    save_deferral.then(function(result) {
                        if(result.res_model != isNaN)
                            if (result.res_model == 'amgl.order_line')
                                location.reload();
                        def_process_save.resolve(result);
                    }).fail(function() {
                        def_process_save.reject();
                    });
                }
            });
        } catch (e) {
            console.error(e);
            return def_process_save.reject();
        }
        return def_process_save;
    },
    do_load_state: function(state, warm) {
        if (state.id && this.datarecord.id != state.id) {
            if (this.dataset.get_id_index(state.id) === null) {
                this.dataset.ids.push(state.id);
            }
            this.dataset.select_id(state.id);
            this.do_show();
        }
    },
    on_button_save: function() {
        var self = this;
        if (this.is_disabled) {
            return;
        }
        this.disable_button();
        return this.save().then(function(result) {
            self.trigger("save", result);
            return self.reload().then(function() {
                if(self.model == 'amgl.customer'){
                    window.location.reload();
                }
                self.to_view_mode();
                core.bus.trigger('do_reload_needaction');
                core.bus.trigger('form_view_saved', self);
            }).always(function() {
                self.enable_button();
            });
        }).fail(function(){
            self.enable_button();
        });
    },
    render_sidebar: function($node) {
        if (!this.sidebar && this.options.sidebar) {
            this.sidebar = new Sidebar(this, {editable: this.is_action_enabled('edit')});
            if (this.fields_view.toolbar) {
                this.sidebar.add_toolbar(this.fields_view.toolbar);
            }
            this.sidebar.add_items('other', _.compact([
                this.is_action_enabled('delete') && { label: _t('Delete'), callback: this.on_button_delete }
            ]));

            this.sidebar.appendTo($node);

            // Show or hide the sidebar according to the view mode
            this.toggle_sidebar();
        }
    },
    });
});
odoo.define('amgl.web.TreeView',function(require){

    "use strict";
    var core = require('web.core');
    var _t = core._t;
    var Model = require('web.DataModel');
	var utils = require('web.utils');
    var TreeView = core.view_registry.get('tree');
    TreeView.include({
        activate: function(id) {
        var self = this;
        var result = self._super(id);

        if (self.model == 'amgl.customer'){

            self.do_action({
                type: 'ir.actions.act_window',
                res_model: self.model,
                view_type: 'form',
                view_mode: 'form',
                target: '_blank',
                res_id: id,
                views: [[false, 'form']],
             });
        }

        return result;
    },
    });

});
odoo.define('amgl.web.UserMenu', function (require) {
    "use strict";
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var Model = require('web.Model');
    var session = require('web.session');
    var Widget = require('web.Widget');
    var _t = core._t;
    var QWeb = core.qweb;
    var UserMenu = require('web.UserMenu')

    UserMenu.include({
    template: "UserMenu",
    start: function() {
        var self = this;
        var Users = new openerp.web.Model('res.users');
        Users.call('has_group', ['amgl.group_amark_admins']).done(function(is_admin) {
            if (!is_admin) {
                self.$el.find(`[data-menu='documentation']`).remove()
                self.$el.find(`[data-menu='settings']`).remove()
                self.$el.find(`[data-menu='account']`).remove()
                self.$el.find(`[data-menu='shortcuts']`).remove()
            }
        });
        this.$el.on('click', '.dropdown-menu li a[data-menu]', function(ev) {
            ev.preventDefault();
            var f = self['on_menu_' + $(this).data('menu')];
            if (f) {
                f($(this));
            }
        });
        return this._super.apply(this, arguments).then(function () {
            return self.do_update();
        });
    }
    });
});
odoo.define('amgl.web.FilterMenu', function (require) {
    "use strict";
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var Model = require('web.Model');
    var session = require('web.session');
    var Widget = require('web.Widget');
    var data_manager = require('web.data_manager');
    var search_filters = require('web.search_filters');
    var search_inputs = require('web.search_inputs');
    var _t = core._t;
    var QWeb = core.qweb;
    var filter_menu = require('web.FilterMenu')

    filter_menu.include({
    template: "SearchView.FilterMenu",
    get_fields: function () {
        if (!this._fields_def) {
            this._fields_def = data_manager.load_fields(this.searchview.dataset).then(function (data) {
                var fields = {
                    id: { string: 'ID', type: 'id', searchable: true }
                };
                _.each(data, function(field_def, field_name) {
                    if (field_def.selectable !== false && field_name !== 'id') {
                        fields[field_name] = field_def;
                    }
                });
                if(fields.create_uid){
                    fields.create_uid.searchable = false
                }
                if(fields.custodian_edit){
                    fields.custodian_edit.searchable = false
                }
                if(fields.create_date){
                    fields.create_date.searchable = false
                }
                if(fields.current_batch_total){
                    fields.current_batch_total.searchable = false
                }
                if(fields.total_weight || fields.total_weight_store || fields.c_total_weight){
                    fields.total_weight.searchable = false
                     fields.total_weight_store.searchable = false
                      fields.c_total_weight.searchable = false
                }
                if(fields.id){
                    fields.id.searchable = false
                }
                if(fields.is_goldstar){
                    fields.is_goldstar.searchable = false
                }
                if(fields.write_uid){
                    fields.write_uid.searchable = false
                }
                if(fields.write_date){
                    fields.write_date.searchable = false
                }
                if(fields.nd_account_number){
                    fields.nd_account_number.searchable = false
                }
                if(fields.show_deposit){
                    fields.show_deposit.searchable = false
                }
                if(fields.state){
                    fields.state.searchable = false
                }
                if(fields.user_id){
                    fields.user_id.searchable = false
                }
                return fields;
            });
        }
        return this._fields_def;
    }
    });
});
odoo.define('amgl.web.GroupByMenu', function (require) {
    "use strict";
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var Model = require('web.Model');
    var session = require('web.session');
    var Widget = require('web.Widget');
    var data_manager = require('web.data_manager');
    var search_filters = require('web.search_filters');
    var search_inputs = require('web.search_inputs');
    var _t = core._t;
    var QWeb = core.qweb;
    var filter_menu = require('web.GroupByMenu')

    filter_menu.include({
    template: "SearchView.GroupByMenu",
    get_fields: function () {
        var self = this;
        if (!this._fields_def) {
            this._fields_def = data_manager.load_fields(this.searchview.dataset).then(function (fields) {
                var groupable_types = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];
                if(fields['create_uid']){
                        fields['create_uid'].searchable = false
                        fields['create_uid'].store = false
                    }
                    if(fields['create_date']){
                        fields['create_date'].searchable = false
                        fields['create_date'].store = false
                    }
                    if(fields['current_batch_total']){
                        fields['current_batch_total'].store = false
                    }
                    if(fields['custodian_edit']){
                        fields['custodian_edit'].store = false
                    }
                    if(fields['total_weight']){
                        fields['total_weight'].store = false
                    }
                    if(fields['total_weight_store']){
                        fields['total_weight_store'].store = false
                    }
                    if(fields['c_total_weight']){
                        fields['c_total_weight'].store = false
                    }
                    if(fields['id']){
                        fields['id'].store = false
                    }
                    if(fields['is_goldstar']){
                        fields['is_goldstar'].store = false
                    }
                    if(fields['write_uid']){
                        fields['write_uid'].store = false
                    }
                    if(fields['write_date']){
                        fields['write_date'].store = false
                    }
                    if(fields['nd_account_number']){
                        fields['nd_account_number'].store = false
                    }
                    if(fields['show_deposit']){
                        fields['show_deposit'].store = false
                    }
                    if(fields['state']){
                        fields['state'].store = false
                    }
                     if(fields['user_id']){
                        fields['user_id'].store = false
                    }
                var filter_group_field = _.filter(fields, function(field, name) {
                    if (field.store && _.contains(groupable_types, field.type)) {
                        field.name = name;
                        return field;
                    }
                });
                self.groupable_fields = _.sortBy(filter_group_field, 'string');

                self.$menu.append(QWeb.render('GroupByMenuSelector', self));
                self.$add_group_menu = self.$('.o_add_group');
                self.$group_selector = self.$('.o_group_selector');
                self.$('.o_select_group').click(function () {
                    self.toggle_add_menu(false);
                    var field = self.$group_selector.find(':selected').data('name');
                    self.add_groupby_to_menu(field);
                });
            });
        }
        return this._fields_def;
    },
    });
});
odoo.define('amgl.web.DataExport', function (require) {
    "use strict";
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var Model = require('web.Model');
    var session = require('web.session');
    var Widget = require('web.Widget');
    var data_manager = require('web.data_manager');
    var search_filters = require('web.search_filters');
    var search_inputs = require('web.search_inputs');
    var _t = core._t;
    var QWeb = core.qweb;
    var crash_manager = require('web.crash_manager');
    var data = require('web.data');
    var pyeval = require('web.pyeval');

    var filter_menu = require('web.DataExport')

    filter_menu.include({
    template: "ExportDialog",
    start: function() {
        var self = this;
        var waitFor = [this._super.apply(this, arguments)];

        this.$fields_list = this.$('.o_fields_list');
        this.$import_compat_radios = this.$('.o_import_compat input');

        waitFor.push(this.rpc('/web/export/formats', {}).then(do_setup_export_formats));

        var got_fields = new $.Deferred();
        this.$import_compat_radios.change(function(e) {
            self.$('.o_field_tree_structure').remove();

            self.rpc("/web/export/get_fields", {
                model: self.dataset.model,
                import_compat: !!$(e.target).val(),
            }).done(function (records) {
                var indexesToBeRemoved = [];
                var itemsToBeRemoved = [];
                $.each(records,function(index, item){
                    if(item){
                        if (item.id == 'custodian_id'){
                            item.value = 'custodian_id/name'
                        }
                        if(item.id == 'create_uid' || item.id == 'create_date' || item.id == 'current_batch_total' || item.id == 'custodian_edit' || item.id == 'total_weight' ||
                            item.id == 'total_weight_store' || item.id == 'c_total_weight' || item.id == 'id' || item.id == 'is_goldstar' || item.id == 'write_uid' ||
                            item.id == 'write_date' || item.id == 'nd_account_number' || item.id == 'show_deposit' || item.id == 'state' || item.id == 'user_id'){

                                indexesToBeRemoved.push(index)
                                itemsToBeRemoved.push(item.id)
                        }
                    }
                })

                var final_fields = $.grep(records, function(n, i){
                    return $.inArray(i, indexesToBeRemoved) == -1;
                })
                records = final_fields
                var compatible_fields = _.map(records, function (record) {return record.id});
                self.$fields_list
                    .find('option')
                    .filter(function () {
                        var option_field = $(this).attr('value');
                        if (compatible_fields.indexOf(option_field) === -1) {
                            return true;
                        }
                    })
                    .remove();
                got_fields.resolve();
                self.on_show_data(records);
            });
        }).eq(0).change();
        waitFor.push(got_fields);

        waitFor.push(this.getParent().get_active_domain().then(function (domain) {
            if (domain === undefined) {
                self.ids_to_export = self.getParent().get_selected_ids();
                self.domain = self.dataset.domain;
            } else {
                self.ids_to_export = false;
                self.domain = domain;
            }
            self.on_show_domain();
        }));

        waitFor.push(this.show_exports_list());

        return $.when.apply($, waitFor);

        function do_setup_export_formats(formats) {
            var $fmts = self.$('.o_export_format');

            _.each(formats, function(format, i) {
                var $radio = $('<input/>', {type: 'radio', value: format.tag, name: 'o_export_format_name'});
                var $label = $('<label/>', {html: format.label});

                if (format.error) {
                    $radio.prop('disabled', true);
                    $label.html(_.str.sprintf("%s — %s", format.label, format.error));
                }

                $fmts.append($("<div/>").append($radio, $label));
            });

            self.$export_format_inputs = $fmts.find('input');
            self.$export_format_inputs.first().prop('checked', true);
        }
    }
    });
});
odoo.define("web_disable_export_group", function(require) {

"use strict";
    var core = require("web.core");
    var Sidebar = require("web.Sidebar");
    var _t = core._t;
    var Model = require("web.Model");
    var session = require("web.session");
    Sidebar.include({
        add_items: function(section_code, items) {
            var self = this;
            var _super = this._super;
            var Users = new openerp.web.Model('res.users');
            var model_res_users = new Model("res.users");
            var can_export = false
            Users.call('has_group', ['amgl.group_amark_admins']).done(function(is_admin) {
                if (is_admin) {
                    can_export = true
                }
                if (!can_export) {
                        var export_label = _t("Export");
                        var new_items = items;
                        if (section_code === "other") {
                            new_items = [];
                            for (var i = 0; i < items.length; i++) {
                                console.log("items[i]: ", items[i]);
                                if (items[i]["label"] !== export_label) {
                                    new_items.push(items[i]);
                                }
                            }
                        }
                        if (new_items.length > 0) {
                            _super.call(self, section_code, new_items);
                        }
                    } else {
                        _super.call(self, section_code, items);
                    }
            });
        }
    });
});
odoo.define('amgl.web.Sidebar', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');
var Sidebar = require('web.Sidebar')
var QWeb = core.qweb;
var _t = core._t;

Sidebar.include({
    add_toolbar: function(toolbar) {
        var self = this;
        _.each(['print','action','relate'], function(type) {
            var items = toolbar[type];
            if (items) {
                var actions = _.map(items, function (item) {
                    return {
                        label: item.name,
                        action: item,
                    };
                });
                var sorted_actions = actions.sort(function (a, b) {
                        var aName = a.label.toLowerCase();
                        var bName = b.label.toLowerCase();
                        return ((aName < bName) ? -1 : ((aName > bName) ? 1 : 0));
                    });
                self.add_items(type === 'print' ? 'print' : 'other', sorted_actions);
            }
        });
    },
});

return Sidebar;

});