from django import forms
from django.utils.html import format_html
from django.utils.encoding import force_str
from django.forms.utils import flatatt
from .models import *

class ImageRadioSelect(forms.RadioSelect):
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        output = []
        options = self.create_options(name, value, attrs)  # Changed from get_options to create_options
        
        for option in options:
            roadsign_id = option.get('value')
            if roadsign_id:
                try:
                    roadsign = RoadSign.objects.get(id=roadsign_id)
                    if roadsign.sign_image:
                        option['label'] = format_html(
                            '{}<br><img src="{}" style="max-height:100px; max-width:150px; margin:5px 0; border:1px solid #ddd;">',
                            option['label'],
                            roadsign.sign_image.url
                        )
                except (RoadSign.DoesNotExist, ValueError):
                    pass
            
            option_attrs = option.get('attrs', {})
            id_ = option_attrs.get('id')
            label_for = format_html(' for="{}"', id_) if id_ else ''
            output.append(
                format_html(
                    '<div style="margin-bottom:15px;">'
                    '<input{}>'
                    '<label{}>{}</label>'
                    '</div>',
                    flatatt(option_attrs),
                    label_for,
                    format_html(option['label'])
                )
            )
        
        return format_html('<div{}>{}</div>', flatatt(attrs), format_html(''.join(output)))

    def create_options(self, name, value, attrs):
        """Create option items for the widget"""
        options = []
        for index, (option_value, option_label) in enumerate(self.choices):
            if option_value is None:
                option_value = ''
            
            option_attrs = self.build_attrs(
                self.build_attrs(attrs, {'type': self.input_type, 'name': name}),
                {'value': force_str(option_value)}
            )
            
            if force_str(option_value) == force_str(value):
                option_attrs['checked'] = True
            
            option_attrs['id'] = attrs.get('id') + '_{}'.format(index)
            
            options.append({
                'name': name,
                'value': option_value,
                'label': force_str(option_label),
                'attrs': option_attrs,
                'type': self.input_type,
            })
        return options