import itertools
import logging


class GlButton(object):

    newid = itertools.count().next
    def __init__(self, texture=None, size=[10.,10.], position=[0.0, 0.0]):
        self.id = (GlButton.newid()+1) * 7013
        self.color_id = [(self.id & 0x000000FF) >> 0, (self.id & 0x0000FF00) >> 8, (self.id & 0x00FF0000) >> 16]

        self.texture = texture
        #logging.debug('Texture type: ' + str(type(self.texture)))
        #logging.debug('Texture: ' + str(self.texture))
        self.size = size
        self.position=position

        self.pressed = False
        self.callback_function = None
        self.press_variable = None

        self.key = None
        self.subkey = None

    def set_callback(self, func):
        self.callback_function = func

    def press_button(self):
        self.pressed = not(self.pressed)
        self.callback_function()


    def unpress_button(self):
        self.pressed = False


    def set_press_variable(self, variable, key, subkey):
        self.press_variable = variable
        self.key = key
        self.subkey = subkey

    def set_viewport(self, width, height):
        self.xW = width
        self.yH = height

    def get_size(self):
        pass

    def render(self, picking=False):
        pass

    def run_callback(self):
        if self.callback_function:
            self.callback_function()

    def check_button(self, color):
        #return True if checked color is same as button color
        #else return False

        color_id = color[0] + (color[1]*255) + (color[2]*255*255)

        if color_id == self.id:
            return True
        else:
            return False




