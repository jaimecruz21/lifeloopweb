const DesktopView = function () {
    const init = function () {
        MobileView.unbind();

        $('#show-signup-desktop').on('click', onClickSignup);
        $('#show-login-desktop').on('click', onClickLogin);

        // DEFAULTS
        $('#navbar').removeClass('transparent');
        $('#login-mobile-toggle, #signup-mobile-toggle').addClass('d-none');
        $('#signup-desktop-toggle').removeClass('d-none');

        $('#signup-col').removeClass('col-lg d-none').addClass('col-lg-auto d-flex');
        $('#login-col').removeClass('col-lg-auto d-none').addClass('col-lg d-flex');
        $('#signup-content').addClass('d-none');
        $('#login-content').removeClass('d-none');
        $('#loginEmail').focus();
    };

    const unbind = function () {
        $('#show-signup-desktop').off('click', onClickSignup);
        $('#show-login-desktop').off('click', onClickLogin);
    };

    const onClickSignup = function (event) {
        event.preventDefault();

        $('#signup-col').addClass('col-lg').removeClass('col-lg-auto');
        $('#signup-content').removeClass('d-none');
        $('#signup-desktop-toggle').addClass('d-none');

        $('#login-col').addClass('col-lg-auto').removeClass('col-lg');
        $('#login-content').addClass('d-none');
        $('#login-desktop-toggle').removeClass('d-none');
    };

    const onClickLogin = function (event) {
        event.preventDefault();

        $('#login-col').addClass('col-lg').removeClass('col-lg-auto');
        $('#login-content').removeClass('d-none');
        $('#login-desktop-toggle').addClass('d-none');

        $('#signup-col').addClass('col-lg-auto').removeClass('col-lg');
        $('#signup-content').addClass('d-none');
        $('#signup-desktop-toggle').removeClass('d-none');
    };

    return {
        init: init,
        unbind: unbind
    };
}();

const MobileView = function () {
    const init = function () {
        DesktopView.unbind();

        $('#show-signup-mobile').on('click', onClickSignup);
        $('#show-login-mobile').on('click', onClickLogin);

        // DEFAULTS
        $('#navbar').addClass('transparent');
        $('#login-desktop-toggle, #signup-desktop-toggle').addClass('d-none');
        $('#login-mobile-toggle, #signup-mobile-toggle').removeClass('d-none');
        $('#login-content, #signup-content').removeClass('d-none');

        $('#signup-col').removeClass('d-flex').addClass('d-none');
        $('#loginEmail').focus();
    };

    const unbind = function () {
        $('#show-signup-mobile').off('click', onClickSignup);
        $('#show-login-mobile').off('click', onClickLogin);
    };

    const onClickSignup = function (event) {
        event.preventDefault();

        $('.navbar .navbar-toggler:not(.collapsed)').click();
        $('#navbar').removeClass('transparent');
        $('#signup-col').removeClass('d-none').addClass('d-flex');
        $('#login-col').removeClass('d-flex').addClass('d-none');
    };

    const onClickLogin = function (event) {
        event.preventDefault();

        $('.navbar .navbar-toggler:not(.collapsed)').click();
        $('#navbar').addClass('transparent');
        $('#login-col').removeClass('d-none').addClass('d-flex');
        $('#signup-col').removeClass('d-flex').addClass('d-none');
    };

    return {
        init: init,
        unbind: unbind
    };
}();

const isMobile = function () {
    return $(window).outerWidth() < breakpoint;
};

const breakpoint = 992;
let DoesCurrentViewIsMobile = isMobile();

const checkIfViewChanged = function () {
    if (!DoesCurrentViewIsMobile && isMobile()) {
        DoesCurrentViewIsMobile = true;
        MobileView.init();
    } else if (DoesCurrentViewIsMobile && !isMobile()) {
        DoesCurrentViewIsMobile = false;
        DesktopView.init();
    }
};

$(window).on('resize', checkIfViewChanged);

if (DoesCurrentViewIsMobile) {
    MobileView.init();
} else {
    DesktopView.init();
}

const onDocumentReady = function () {
    if (window.location.hash.substr(1) === 'signup') {
        if (DoesCurrentViewIsMobile) {
            $('#show-signup-mobile').click();
        } else {
            $('#show-signup-desktop').click();
        }
    }
};

$(document).ready(onDocumentReady);
