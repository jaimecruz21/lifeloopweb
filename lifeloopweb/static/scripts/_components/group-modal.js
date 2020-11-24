let GroupModal = function () {
    let $target,
        $self,
        $body,
        $card;

    let init = function () {
        $self = $('#groupModal');
        $body = $self.find('.modal-body');

        $self.on('show.bs.modal', onShow);
    };

    let onShow = function (event) {
        $target = $(event.relatedTarget);
        $card = $target.closest('.card').clone(true);
        $card.addClass('modal-nested');
        let $description = $card.find('.ll-description');
        $description.removeAttr('style');
        $description.find('a').remove();
        $body.html($card);
    };

    return {
        init: init
    };
}();

export {GroupModal};
