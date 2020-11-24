const path = require('path');
const webpack = require('webpack');
const CleanWebpackPlugin = require('clean-webpack-plugin');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const ManifestRevisionPlugin = require('manifest-revision-webpack-plugin');

const rootAssetPath = './lifeloopweb/static';

function get_entries(dir, ext, filenames) {
    let obj = {};
    for (let filename of filenames) {
        obj[filename] = rootAssetPath + dir + '/' + filename + '.' + ext
    }
    return obj;
}

const stylesEntries = get_entries('/styles', 'scss', [
    'main',
    'vendor'
]);

const scriptsEntries = get_entries('/scripts', 'js', [
    'global',
    'forgot-password',
    'group-new',
    'group-edit',
    'group-view',
    'homepage',
    'login',
    'organization-new',
    'organization-edit',
    'organization-view',
    'organization-view-sort-groups',
    'register-after-email',
    'reset-password',
    'subscribe',
    'user'
]);

const fileLoaderRule = 'file-loader?context=' + rootAssetPath + '&name=[path][name].[hash].[ext]';

const rules = [{
    test: /\.js$/,
    loader: 'babel-loader',
    exclude: /node_modules/
}, {
    test: /\.scss$/,
    include: [
        path.resolve(__dirname, rootAssetPath + '/styles')
    ],
    use: ExtractTextPlugin.extract({
        fallback: 'style-loader',
        use: ['css-loader', 'sass-loader', 'postcss-loader']
    })
}, {
    test: /\.(ico|png|jpe?g)$/,
    loader: fileLoaderRule
}, {
    test: /\.(eot([\?]?.*)|ttf([\?]?.*)|woff([\?]?.*)|woff2([\?]?.*)|svg([\?]?.*))$/,
    loader: 'file-loader?context=' + rootAssetPath + '&name=fonts/[path][name].[hash].[ext]'
}, {
    test: /\.(html)$/,
    loader: fileLoaderRule
}];

module.exports = env => {
    if (typeof env === 'undefined') {
        env = {};
    }

    const plugins = [
        new ExtractTextPlugin('css/[name].[chunkhash].css'),
        new CleanWebpackPlugin('lifeloopweb/build'),
        new webpack.optimize.CommonsChunkPlugin({
            name: 'global'
        }),
        new ManifestRevisionPlugin(path.join('lifeloopweb/build', 'manifest.json'), {
            rootAssetPath: rootAssetPath,
            ignorePaths: ['/fonts', '/styles']
        }),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.$': 'jquery',
            'window.jQuery': 'jquery',
            Popper: ['popper.js', 'default'],
            Chart: 'chart.js',
            moment: 'moment-timezone',
            cloudinary: 'cloudinary-core',
            rome: 'rome'
        }),
        new webpack.DefinePlugin({
            PRODUCTION: env.hasOwnProperty('PRODUCTION')
        })
    ];

    return {
        entry: Object.assign(stylesEntries, scriptsEntries),
        devtool: 'inline-source-map',
        watchOptions: {
            ignored: /node_modules/,
            poll: true
        },
        output: {
            path: path.resolve(__dirname, 'lifeloopweb/build'),
            publicPath: '/build/',
            filename: '[name].[hash].js',
            chunkFilename: '[id].[chunkhash].js'
        },
        resolve: {
            extensions: ['.js', '.scss']
        },
        module: {
            rules: rules
        },
        plugins: plugins
    }
};
