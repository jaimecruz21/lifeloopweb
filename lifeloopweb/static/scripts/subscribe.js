const NumberOfGroupLeaders = function () {
    let $self,
        prices;
    const prefix = '#billing-';

    const init = function () {
        $self = $('#quantity');
        $self.on('change paste keyup', onChange);
        base = $('[data-base]').data('base') * 1;
        prices = $('[data-prices]').data('prices');
        discount = $(prefix + 'discount').data('discount') * .01 || 1;
        onChange();
    };

    const onChange = function () {
        let matched;

        for (let i in prices) {
            if (prices.hasOwnProperty(i)) {
                if ($self.val() >= prices[i]['starting_quantity']) {
                    matched = prices[i];
                }
            }
        }

        if (matched) {
            let price = matched['unit_price'] * 1;
            $(prefix + 'quantity').html($self.val() + ' ' + ($self.val() * 1 === 1 ? 'License' : 'Licenses'));
            $(prefix + 'price').html(matched['formatted_unit_price']);
            $(prefix + 'total').html('$' + $self.val() * price);
            $(prefix + 'total').html('%' + discount);
            $(prefix + 'final').html('$' + (($self.val() * price + base) * discount).toFixed(2));
        }
    };

    return {
        init: init
    };
}();

NumberOfGroupLeaders.init();
