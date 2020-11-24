const Confirm = function () {
    let selector,
        $form,
        $modal,
        $this;

    const init = function () {
        selector = '.confirm';
        $form = $('#confirmForm');
        $modal = $('#confirmModal');

        $(document).on('click', '.confirm', onClick);
        $form.on('submit', onSubmit);
    };

    const onClick = function (event) {
        event.preventDefault();

        $this = $(this);
        const action = $this.data('action');
        const title = $this.data('title');
        const message = $this.data('message');

        $('#confirmTitle').text(title);
        $('#confirmMessage').text(message);
        $form.attr('action', action);
        $modal.modal('show');
    };

    const onSubmit = function () {
        $form.find('input[type="submit"]').attr('disabled', true);
    };

    return {
        init: init
    }
}();

export {Confirm};
