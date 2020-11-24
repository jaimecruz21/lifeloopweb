const MemberChangeStatus = function () {
    let $self,
        $modal,
        $message,
        $form,
        $submit,
        $cohost,
        $this;

    let fullname,
        description,
        action;

    const init = function () {
        $self = $('[data-change-role-id]');
        $modal = $('#confirmRoleModal');
        $message = $('#changeRoleMessage');
        $cohost = $('.js-cohost');

        if ($cohost.length) {
            $cohost.on('click', onClickCohost);
        }

        $self.on('click', onClick);
    };

    const onClickCohost = function () {
        $this = $(this);
        $form = $this.closest('form');
        $submit = $('#confirmRoleSubmit').attr('form', $form.attr('id'));

        fullname = makeStrong($form.data('userFullname'));

        if ($this.is(':checked')) {
            action = 'Assign';
        } else {
            action = 'Unassign';
        }

        $message.html(action + ' an alternative host to ' + fullname);

        $form.find('[name="role"]').val($form.data('userRoleId'));
        $modal.modal('show');

        $modal.on('hide.bs.modal', function () {
            $this.prop('checked', !$this.prop('checked'));
            $modal.off('hide.bs.modal');
        });
    };

    const onClick = function (event) {
        event.preventDefault();

        $this = $(this);
        $form = $this.closest('form');
        $submit = $('#confirmRoleSubmit').attr('form', $form.attr('id'));

        if ($this.hasClass('disabled')) {
            return false;
        }

        fullname = makeStrong($form.data('userFullname'));
        description = makeStrong($this.data('changeRoleDescription'));

        $message.html('Set ' + description + ' role to ' + fullname);

        $form.find('[name="role"]').val($this.data('changeRoleId'));
        $modal.modal('show');
    };

    const makeStrong = function (text) {
        return $('<strong />', {'text': text})[0].outerHTML;
    };

    return {
        init: init
    }
}();

export {MemberChangeStatus};
