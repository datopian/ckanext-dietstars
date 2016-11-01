import copy
import json

import pylons.config as config

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h

from webhelpers.html import literal


def extended_build_nav(*args):
    # we go through the args, add links for raw links, and then pass the rest to core build_nav_main
    output = ''
    for item in args:
        menu_item, title = item[:2]

        if len(item) == 3 and not check_access(item[2]):
            continue

        if menu_item.startswith('http') or menu_item.startswith('/'):
            # it's a link
            output += literal('<li><a href="%s">%s</a></li>' % (menu_item, title))
        else:
            # give it to the core helper for this
            output += h._make_menu_item(menu_item, title)
    return output

open_licenses = ['cc-by', 'psi']
five_star_formats = ['rdf', 'n3', 'sparql', 'ttl']
four_star_formats = []
three_star_formats = ["kml", "wcs", "netcdf", "tsv", "wfs", "kmz", "qgis", "ods", "json", "odb", "odf", "odg", "xml", "wms", "wmts", "svg", "jpeg", "csv", "atom feed", "xyz", "png", "rss", "geojson", "iati", "ics",]
two_star_formats = ['shp', "xls", "mdb", "arcgis map service", "bmp", "tiff", "xlsx", "gif", "e00", "mrsid", "arcgis map preview", "mop", "esri rest", "dbase"]

def get_qa_dict(pkg_dict):
    # we'll use the same format the ckanext-qa extension uses
    qa_dict = {'openness_score_reason': '', 'openness_score': 0}

    license_id = pkg_dict.get('license_id')
    # pretty easy - first check if the license is open
    if (license_id not in open_licenses):
        qa_dict['openness_score_reason'] = 'The dataset license is not in our list of Open Licenses.'
        return qa_dict

    # now it's at least 1-star
    qa_dict['openness_score'] = 1
    qa_dict['openness_score_reason'] = 'The dataset license is an open license'

    # now we pretty much just compare formats
    resource_formats = [r.get('format').lower() for r in pkg_dict.get('resources')]

    share_elements = lambda a, b: not set(a).isdisjoint(set(b))

    if (share_elements(resource_formats, five_star_formats)):
        qa_dict['openness_score'] = 5
        qa_dict['openness_score_reason'] = 'One of the resource formats is 5-star data - linked data.'
    elif (share_elements(resource_formats, four_star_formats)):
        qa_dict['openness_score'] = 4
        qa_dict['openness_score_reason'] = 'One of the resource formats is 4-star data - data that uses URIs.'
    elif (share_elements(resource_formats, three_star_formats)):
        qa_dict['openness_score'] = 3
        qa_dict['openness_score_reason'] = 'One of the resource formats is 3-star data - machine-readable data in an open format.'
    elif (share_elements(resource_formats, four_star_formats)):
        qa_dict['openness_score'] = 2
        qa_dict['openness_score_reason'] = 'One of the resource formats is 2-star data - machine-readable data in a proprietary format.'

    return qa_dict

def qa_openness_stars_resource_html(resource):
    qa = resource.get('qa')
    if not qa:
        return toolkit.literal('<!-- No qa info for this resource -->')
    if not isinstance(qa, dict):
        return toolkit.literal('<!-- QA info was of the wrong type -->')

    # Take a copy of the qa dict, because weirdly the renderer appears to add
    # keys to it like _ and app_globals. This is bad because when it comes to
    # render the debug in the footer those extra keys take about 30s to render,
    # for some reason.
    extra_vars = copy.deepcopy(qa)
    return toolkit.literal(
        toolkit.render('qa/openness_stars.html',
                  extra_vars=extra_vars))


def qa_openness_stars_dataset_html(dataset):
    qa = dataset.get('qa')
    if not qa:
        return toolkit.literal('<!-- No qa info for this dataset -->')
    if not isinstance(qa, dict):
        return toolkit.literal('<!-- QA info was of the wrong type -->')
    extra_vars = copy.deepcopy(qa)
    return toolkit.literal(
        toolkit.render('qa/openness_stars_brief.html',
                  extra_vars=extra_vars))

class DietStarsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'dietstars')

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'extended_build_nav': extended_build_nav,
            'qa_openness_stars_resource_html': qa_openness_stars_resource_html,
            'qa_openness_stars_dataset_html': qa_openness_stars_dataset_html
        }

    # IPackageController

    def before_index(self, search_dict):
        # we add the QA dict here so we can facet
        # print pkg_dict
        pkg_dict = json.loads(search_dict['data_dict'])
        search_dict['openness_score'] = get_qa_dict(pkg_dict)['openness_score']
        return search_dict

    def before_view(self, pkg_dict):
        # add the QA dict here so we can show it :)
        pkg_dict['qa'] = get_qa_dict(pkg_dict)
        return pkg_dict

    def after_show(self, context, pkg_dict):
        # add the QA dict here so we can show it :)
        pkg_dict['qa'] = get_qa_dict(pkg_dict)
        return pkg_dict

    # IFacets

    def dataset_facets(self, facets_dict, package_type):
        if (package_type == 'dataset'):
            facets_dict['openness_score'] = plugins.toolkit._('Openness')
        return facets_dict
