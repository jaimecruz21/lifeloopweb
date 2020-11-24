let Search = function () {
    let $search;
    const $BODY = $('body');
    const $NAVBAR = $('#navbar');
    let mobileTimeout;
    let $this;

    const init = function () {
        $search = $('#searchDropdown').parent();

        $(document).on('click', '.dropdown-menu', onClick);
        $search.on('show.bs.dropdown', onSearch);
        $('.js-mobile-search-form input[name="name"]').on('keyup input', onMobileKeyup);
        $('#mobileSearch .search-close').on('click', onMobileCloseClick);
    };

    const onSearch = function (event) {
        if ($BODY.hasClass('mobile')) {
            event.preventDefault();

            $NAVBAR.find('.navbar-brand').hide();
            $('#mobileSearch').parent().removeClass('ml-auto flex-row pr-2').addClass('d-block w-100');
            $('#searchDropdown').removeClass('d-flex').hide();
            $('#userNotifications').hide();
            $('.navbar-toggler').hide();
            $('#mobileSearch').addClass('d-flex justify-content-between align-items-center');
        }
    };

    const onMobileKeyup = function () {
        window.clearTimeout(mobileTimeout);
        $this = $(this);

        if ($this.val().length) {
            mobileTimeout = window.setTimeout(onMobileTimeout($(this)), 3000);
        }
    };

    const onMobileTimeout = function ($this) {
        return function () {
            $this.closest('form').submit();
        }
    };

    const onClick = function (event) {
        event.stopPropagation();
    };

    const onMobileCloseClick = function (event) {
        event.preventDefault();

        $NAVBAR.find('.navbar-brand').show();
        $('#mobileSearch').parent().addClass('ml-auto flex-row pr-2').removeClass('d-block w-100');
        $('#searchDropdown').addClass('d-flex').show();
        $('#userNotifications').show();
        $('.navbar-toggler').show();
        $('#mobileSearch').removeClass('d-flex justify-content-between align-items-center');

        $(this).off('click');
    };

    return {
        init: init
    };
}();

export {Search};
