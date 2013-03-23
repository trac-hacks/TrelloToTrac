import re


class MarkdownToWiki():
    text = ''

    def __init__(self, text):
        self.text = text
        
    def convert(self):
        text = self.text
        text = re.sub('\r\n', '\n', text)
        #bold
        text = re.sub(r'\*\*(.*?)\*\*',r"'''\1'''", text)
        #italics
        text = re.sub(r'_(.*?)_',r"''\1''", text)
        #@TODO
        #make BR
        self.text = text
        return self.text
