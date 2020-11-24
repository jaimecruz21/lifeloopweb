const PasswordValidator = function () {
    'use strict';

    let $confirm,
        $password,
        $submit;

    let confirm,
        password,
        testsPassed;

    const init = function () {
        $password = $('#txtPassword');
        $confirm = $('#confirm');
        $submit = $('#passwordSubmit');

        $password.keyup(onKeyup);
        $confirm.keyup(onKeyup);

        checkSuccess();
    };

    const onKeyup = function () {
        confirm = $confirm.val();
        password = $password.val();
        testsPassed = 0;

        check($('#length-req'), password.length >= 8);
        check($('#lower-req'), /[a-z]+/.test(password));
        check($('#upper-req'), /[A-Z]+/.test(password));
        check($('#number-req'), /[0-9]+/.test(password));
        check($('#special-req'), /[^\w]/.test(password));
        check($('#match-req'), password === confirm);

        checkSuccess();
    };

    const checkSuccess = function () {
        if (testsPassed === 6) {
            $submit.attr('disabled', false);
        } else {
            $submit.attr('disabled', true);
        }
    };

    function check($reqSpan, bool) {
        if (bool) {
            $reqSpan.css('color', '#08a708');
            testsPassed++;
        } else {
            $reqSpan.css('color', '#ff2460');
        }
    }

    return {
        init: init
    }
}();

export {PasswordValidator};
