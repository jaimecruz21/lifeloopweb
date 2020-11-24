const LinkModal = function () {
    let $self,
        $form,
        $target,
        $select,
        $input,
        $submit;

    const init = function () {
        $self = $('#linkModal');
        $form = $('#linkForm');
        $select = $form.find('#link_type');
        $input = $form.find('#link');
        $submit = $form.find('#linkFormSubmit');

        $self.on('show.bs.modal', onShow);
    };

    const onShow = function (event) {
        $target = $(event.relatedTarget);
        $form.attr('action', $target.data('action'));
        $select.val($select.find('option:contains(' + $target.data('typeValue') + ')').val());
        $input.val($target.data('linkValue'));
        $submit.val($target.data('btn'));
    };

    return {
        init: init
    }
}();

export {LinkModal};
