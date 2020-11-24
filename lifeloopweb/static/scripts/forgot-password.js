import $ from 'jquery';

const ForgotPassword = function () {
    const init = function () {
        $('#email').focus();
    };

    return {
        init: init
    }
}();

ForgotPassword.init();
