import {AutoComplete} from './_components/owner-autocomplete';

const CheckOrgLicenses = function () {
    let $org,
        org_choices_array;

    const init = function () {
        $org = $('#org');
        org_choices_array = $.map($org.children(), mapOrgChoices);

        if ($('body').data('is-subscription-on')) {
            $org.on('change', onChange);
        }
    };

    const mapOrgChoices = function (option) {
        if (option.value) {
            return option.value;
        }
    };

    const onChange = function () {
        if (org_choices_array.indexOf($org.val()) !== -1) {
            $.post(window.location, {'org_id': $org.val()}, onPost);
        }
    };

    const onPost = function (response) {
        console.log(response.licenses);
    };

    return {
        init: init
    }
}();

AutoComplete.init();
CheckOrgLicenses.init();
