from os.path import join
from lxml import etree
import numpy as np
from collections import namedtuple
from pathlib import Path


class Conrad_XML:
    def __init__(self, conradxml=join(str(Path.home()), 'Conrad.xml')):
        tree = etree.parse(conradxml)
        self.root = tree.getroot()
        self.geometry = self.root.find(".//void[@property='geometry']")
        self.projection = self.root.find(".//array[@class='edu.stanford.rsl.conrad.geometry.Projection']")

    def get_projection_matrices(self):
        numProjMats = int(self.projection.attrib['length'])
        projMats = np.ndarray(shape=(numProjMats, 3, 4))
        for idx in self.projection.findall(".//void[@index]"):
            pMatString = idx.find(".//void[@property='PMatrixSerialization']").getchildren()[0].text
            for c in list('[];'):
                pMatString = pMatString.replace(c, '')
            pMat = np.fromstring(pMatString, dtype=np.float64, sep=' ').reshape(3, 4)
            projMats[int(idx.attrib['index'])] = pMat
        return projMats

    def get_num_projection_matrices(self):
        return int(self.projection.attrib['length'])

    def get_detector_dims(self):
        detectorHeight = int(self.geometry.find(".//void[@property='detectorHeight']").getchildren()[0].text)
        detectorWidth = int(self.geometry.find(".//void[@property='detectorWidth']").getchildren()[0].text)
        dims = namedtuple('detectorDimensions', ['height', 'width'])
        return dims(height=detectorHeight, width=detectorWidth)

    def get_pixel_dims(self):
        pixelDimensionY = float(self.geometry.find(".//void[@property='pixelDimensionY']").getchildren()[0].text)
        pixelDimensionX = float(self.geometry.find(".//void[@property='pixelDimensionX']").getchildren()[0].text)
        dims = namedtuple('pixelDimensions', ['y', 'x'])
        return dims(y=pixelDimensionY, x=pixelDimensionX)

    def get_primary_angles(self):
        primaryAnglesString = self.geometry.find(".//void[@property='primaryAnglesString']").getchildren()[0].text
        return np.fromstring(primaryAnglesString, dtype=np.float64, sep=' ')

    def get_reco_dims(self):
        reconDimensionX = int(self.geometry.find(".//void[@property='reconDimensionX']").getchildren()[0].text)
        reconDimensionY = int(self.geometry.find(".//void[@property='reconDimensionY']").getchildren()[0].text)
        reconDimensionZ = int(self.geometry.find(".//void[@property='reconDimensionZ']").getchildren()[0].text)
        dims = namedtuple('reconstructionDimensions', ['z', 'y', 'x'])
        return dims(z=reconDimensionZ, y=reconDimensionY, x=reconDimensionX)

    def get_reco_voxel_dims(self):
        reconVoxelSizes = self.geometry.find(".//void[@property='reconVoxelSizes']")
        # not sure if the order here is z,y,x or x,y,z --> conrad is inconsistent with the order :(
        voxelDimZ = float(reconVoxelSizes.find(".//void[@index='0']").getchildren()[0].text)
        voxelDimY = float(reconVoxelSizes.find(".//void[@index='1']").getchildren()[0].text)
        voxelDimX = float(reconVoxelSizes.find(".//void[@index='2']").getchildren()[0].text)
        dims = namedtuple('reconstructionVoxelDimensions', ['z', 'y', 'x'])
        return dims(z=voxelDimZ, y=voxelDimY, x=voxelDimX)

    def get_sdd_sid(self):
        sdd = float(self.geometry.find(".//void[@property='sourceToDetectorDistance']").getchildren()[0].text)
        sid = float(self.geometry.find(".//void[@property='sourceToAxisDistance']").getchildren()[0].text)
        sdd_sid = namedtuple('sdd_sid', ['sourceToDetectorDistance', 'sourceToAxisDistance'])
        return sdd_sid(sourceToDetectorDistance=sdd, sourceToAxisDistance=sid)


if __name__ == '__main__':
    c = Conrad_XML()
    projMats = c.get_projection_matrices()
    print(projMats[0])
    print(c.get_detector_dims())
    print(c.get_pixel_dims())
    print(c.get_primary_angles())
    print(c.get_reco_voxel_dims())
    print(c.get_sdd_sid())