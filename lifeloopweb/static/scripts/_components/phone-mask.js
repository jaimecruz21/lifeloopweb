import 'jquery-mask-plugin';

const PhoneMask = function () {
    const config = '(999) 999-9999';

    const init = function (selector) {
        if (typeof selector === 'undefined') {
            selector = '#phone_number';
        }

        $(selector).mask(config, {placeholder: '(___) ___-____'});
    };

    return {
        init: init
    }
}();

export {PhoneMask};
