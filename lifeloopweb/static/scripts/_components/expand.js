let Expand = function () {
    let $self;

    let init = function () {
        $(window).on('resize', onResize);
        $(window).resize();
    };

    let onResize = function () {
        $self = $('[data-content]');

        let onClick = function (event) {
            event.preventDefault();

            let $self = $(this),
                $content = $(this).siblings();

            $content.fadeOut(300, function () {
                $content.attr('style', 'display: none;');
                $self.remove();
                $content.fadeIn(300);
            });
        };

        let Anchor = {
            'expand': function () {
                return $('<a>', {
                    'text': 'more',
                    'href': '#',
                    'class': 'show-more'
                });
            }(),
            'modal': function () {
                let $anchor = $('<a>', {
                    'text': 'MORE',
                    'href': '#',
                    'data-toggle': 'modal',
                    'data-target': '#groupModal'
                });

                $anchor.addClass('text-danger');
                $anchor.css({
                    'position': 'absolute',
                    'right': 0,
                    'bottom': 0,
                    'padding-left': '5px',
                    'background-color': '#ffffff',
                    'box-shadow': '-5px 0px 5px -3px #ffffff',
                    'outline': 0
                });

                return $anchor;
            }()
        };

        let css = {
            'overflow': 'hidden',
            'margin-bottom': '10px'
        };

        let $anchor;
        let maxHeight;

        $.each($self, function () {
            $anchor = {};

            switch ($(this).data('content')) {
                case 'expand':
                    maxHeight = 60;
                    css['max-height'] = maxHeight + 'px';

                    let height = $(this).height();

                    if (height > maxHeight) {
                        $anchor = Anchor.expand.clone();

                        $(this).css(css);
                        $(this).parent().append($anchor);
                        $anchor.on('click', onClick);
                    }
                    break;

                case 'modal':
                    maxHeight = 120;
                    css['max-height'] = maxHeight + 'px';
                    if (!$(this).children().length && $(this).height() > maxHeight) {
                        $anchor = Anchor.modal.clone();

                        $(this).addClass('position-relative');
                        $(this).css(css);
                        $(this).append($anchor);
                    }
                    break;
            }
        });
    };

    return {
        init: init
    };
}();

export {Expand};
