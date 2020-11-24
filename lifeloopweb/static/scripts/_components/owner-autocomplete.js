import 'jquery-ui/ui/widgets/autocomplete';
import {Alert} from './alert';

const AutoComplete = function () {
    let $field;

    const init = function (selector) {
        if (typeof selector === 'undefined') {
            selector = '#owner';
        }

        $field = $(selector);

        $field.autocomplete({
            'appendTo': $field.parents(2),
            'minLength': 1,
            'source': source,
            'select': select
        });

        $('#user_is_leader').on('click', onClick);
    };

    const onClick = function () {
        $('#owner-wrapper').toggleClass('d-none');
        $field.attr('required', function (_, attr) {return !attr});
    };

    const source = function (request, response) {
        let url = '/users?prefix=' + request.term;
        const org_id = $('#org').find(':selected').val();

        if (org_id) {
            url += '&org_id=' + org_id;
        }

        $.ajax({
            url: url,
            dataType: 'json',
            type: 'GET',
            contentType: 'application/json; charset=utf-8',
            success: onSuccess(response),
            fail: onFail
        });
    };

    const select = function (e, i) {
        $('#owner_last_name').val(i.item.label);
    };

    const onSuccess = function (response) {
        return function (json) {
            response($.map(json, function (member) {
                return {
                    label: member.name,
                    val: member.id
                };
            }));
        };
    };

    const onFail = function (json) {
        Alert.add('Failure searching for organization owner. Please try again later', 'danger');
    };

    return {
        init: init
    };
}();

export {AutoComplete};
