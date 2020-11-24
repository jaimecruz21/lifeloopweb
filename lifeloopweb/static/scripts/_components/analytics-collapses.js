const AnalyticsCollapses = function () {
    let $toggle;
    let $self;

    const init = function () {
        $toggle = $('#analyticsToggle');
        $self = $('#org-edit-db-analytics, #org-edit-google-analytics1, #org-edit-google-analytics2');

        $toggle.on('click', onClick);
        $self.on('show.bs.collapse', onShow);
        $self.on('hidden.bs.collapse', onHide);
    };

    const onClick = function () {
        $toggle.contents().filter(function () {
            return this.nodeType === 3
        }).each(function () {
            if ($toggle.hasClass('collapsed')) {
                this.textContent = this.textContent.replace('View', 'Hide');
            } else {
                this.textContent = this.textContent.replace('Hide', 'View');
            }
        });
    };

    const onShow = function () {
        $(this).css('display', 'flex');
    };

    const onHide = function () {
        $(this).removeAttr('style');
    };

    return {
        init: init
    };
}();

export {AnalyticsCollapses};
