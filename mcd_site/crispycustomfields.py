from crispy_forms.layout import Field

class dropdownField(Field):
    template='crispy-templates/search-dropdown.html'
    
class inlineField(Field):
    template='crispy-templates/inlineField.html'

class dateField(Field):
    template='crispy-templates/dateField.html'

class iconField(Field):
    template='crispy-templates/iconField.html'
    
class checkbox(Field):
    template ='crispy-templates/checkbox.html'
    
class transparentInput(Field):
    template ='crispy-templates/transparentinput.html'
       
    