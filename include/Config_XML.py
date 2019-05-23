import os
from lxml import etree
import numpy as np
from collections import namedtuple

class Config_XML():
    def __init__(self):
        self.config = {}
        self.project_dir = '.'

    def init_config(self):
        self.config['mesh_filename'] = os.path.realpath(os.path.join(self.project_dir, 'data', 'phantom.stl'))
        self.config['phantom_filename'] = os.path.realpath(os.path.join(self.project_dir, 'data', 'phantom.npz'))
        self.config['mesh_rot'] = np.zeros(3)
        self.config['mesh_trans'] = np.zeros(3)
        self.config['mesh_scale'] = np.ones(3)
        self.config['mesh_color'] = np.array([0.69411765, 0.47843137, 0.39607843])

    def read(self, filename):
        tree = etree.parse(filename)
        root = tree.getroot()
        self.config['phantom_filename'] = os.path.realpath(os.path.join(self.project_dir, root.find('PhantomFilename').attrib['value']))
        self.config['mesh_filename'] = os.path.realpath(os.path.join(self.project_dir, root.find('MeshFilename').attrib['value']))
        self.config['mesh_rot'] = np.fromstring(root.find('MeshRotation').attrib['value'], sep=' ')
        self.config['mesh_trans'] = np.fromstring(root.find('MeshTranslation').attrib['value'], sep=' ')
        self.config['mesh_scale'] = np.fromstring(root.find('MeshScale').attrib['value'], sep=' ')
        self.config['mesh_color'] = np.fromstring(root.find('MeshColor').attrib['value'], sep=' ')

    def write(self, filename):
        root = etree.Element('InteractiveConeBeamReconstruction', version='0.1')
        etree.SubElement(root, 'PhantomFilename', value=self.config['phantom_filename'].replace(os.path.realpath('..'), '')[1:])
        etree.SubElement(root,'MeshFilename', value=self.config['mesh_filename'].replace(os.path.realpath('..'), '')[1:])
        etree.SubElement(root, 'MeshRotation', value=np.array2string(self.config['mesh_rot'])[1:-1])
        etree.SubElement(root, 'MeshTranslation', value=np.array2string(self.config['mesh_trans'])[1:-1])
        etree.SubElement(root, 'MeshScale', value=np.array2string(self.config['mesh_scale'])[1:-1])
        etree.SubElement(root, 'MeshColor', value=np.array2string(self.config['mesh_color'])[1:-1])
        tree = etree.ElementTree(root)
        tree.write(filename, encoding='utf8', method='xml', pretty_print=True)

if __name__ == '__main__':
    c = Config_XML()
    c.init_config()
    c.write('test.xml')
    c.read('test.xml')
    print(c.config)
