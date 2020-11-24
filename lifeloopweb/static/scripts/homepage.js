import {Confirm} from './_components/confirm';

const Homepage = function () {
    const $LOADER = $('.loader');

    const init = function () {
        WindowOnScroll.init();
        Filter.init();
    };

    const WindowOnScroll = function () {
        const init = function () {
            $(window).on('scroll', onScroll);
            $(window).scroll();
            $LOADER.fadeOut(function () {
                this.parentNode.removeChild(this);
            });
        };

        const onScroll = function () {
            LoadMore();
            $(window).resize();
        };

        const LoadMore = function () {
            const $wrapper = $('#featuredGroups');

            if ($wrapper.offset().top + $wrapper.height() - $(window).scrollTop() - $(window).height() < 400) {
                $wrapper.find('.card.d-none:lt(4)').fadeIn(1200, LoadMore).removeClass('d-none');
            }
        };

        return {
            init: init
        };
    }();

    const Filter = function () {
        let timeoutReference,
            $dropdowns;

        let savedValues = {},
            currentValues = {};

        const init = function () {
            const $wrapper = $('nav.filter');
            $dropdowns = $wrapper.find('.dropdown');

            $dropdowns.find('.dropdown-item').on('click', onClick);
            $dropdowns.on('show.bs.dropdown', onShow);
            $dropdowns.on('hide.bs.dropdown', onHide);

            setDefaultActive();
        };

        // By default, every filter`s 1st item is active
        const setDefaultActive = function () {
            let $item,
                $filter;

            const onEach = function (i, el) {
                $filter = $(el);
                $item = $filter.find('.dropdown-item:first');
                $item.addClass('active');
            };

            $.each($dropdowns, onEach);
        };

        const onClick = function (event) {
            event.preventDefault();

            const $item = $(this);
            const $dropdown = $item.closest('.dropdown');
            const $toggle = $dropdown.find('.dropdown-toggle');
            const filterName = $dropdown.data('name');

            // Multiple dropdown selection
            if ($dropdown.hasClass('ll-multiple')) {
                event.stopPropagation();

                const $all = $dropdown.find('.ll-all');

                // Clicked 'all' dropdown option
                if ($item.hasClass('ll-all')) {
                    // Already showing all
                    if ($item.hasClass('active')) {
                        return false;
                    }

                    $dropdown.find('.dropdown-item').removeClass('active');
                    $all.addClass('active');
                    delete currentValues[filterName];
                    $toggle.text($item.text());
                // Clicked dropdown option
                } else {
                    $all.removeClass('active');
                    $item.toggleClass('active');

                    if (typeof currentValues[filterName] === 'undefined') {
                        currentValues[filterName] = [];
                    }

                    // Add new item
                    if ($item.hasClass('active')) {
                        currentValues[filterName].push($item.data('value'));
                    // Remove item
                    } else {
                        currentValues[filterName].splice(
                            currentValues[filterName].indexOf($item.data('value')),
                            1
                        );
                    }

                    // No items selected = show all
                    if (!currentValues[filterName].length) {
                        delete currentValues[filterName];
                        return $all.click();
                    // One or more items selected
                    } else {
                        let plural = $all.text().split(' ').pop();

                        // Singular
                        if (currentValues[filterName].length === 1) {
                            if (plural.slice(-3, plural.length) === 'ies') {
                                plural = plural.slice(0, -3) + 'y';
                            } else {
                                plural = plural.slice(0, -1);
                            }
                        }

                        // Selected all items one-by-one
                        if (currentValues[filterName].length === $item.parent().children().length -1) {
                            $toggle.text($all.text());
                        // Selected some items
                        } else {
                            $toggle.text(currentValues[filterName].length + ' ' + plural);
                        }
                    }
                }
            // Single dropdown selection
            } else {
                // Already selected
                if ($item.hasClass('active')) {
                    return false;
                }

                // Clicked one Default value, remove it from filter
                if ($item.data('value') ===
                    $dropdown.find('.dropdown-item:first').data('value')) {
                    delete currentValues[filterName];
                // Change
                } else {
                    currentValues[filterName] = $item.data('value');
                }

                $toggle.text($item.text());
                $dropdown.find('.dropdown-item').removeClass('active');
                $item.addClass('active');
            }
        };

        const onShow = function (event) {
            if (timeoutReference) {
                clearTimeout(timeoutReference);
            }
        };

        const onHide = function (event) {
            if (timeoutReference) {
                clearTimeout(timeoutReference);
            }

            timeoutReference = setTimeout(function() {
                if (JSON.stringify(savedValues) !==
                    JSON.stringify(currentValues)) {
                    $('#featuredGroups').css('opacity', '.5');

                    $.ajax({
                        url: window.location,
                        type: 'POST',
                        data: JSON.stringify(currentValues),
                        contentType: 'application/json',
                        complete: function (response) {
                            if (response.status === 200) {
                                savedValues = JSON.parse(JSON.stringify(currentValues));
                                $('#featuredGroups').css('opacity', '1')
                                                    .html(response.responseText);
                                $(window).scroll();
                            }
                        }
                    });
                }
            }, 800);
        };

        return {
            init: init
        };
    }();

    return {
        init: init
    };
}();

Confirm.init();
Homepage.init();
