# Functions used in Interpenetrating MOFs project
# for the calculation energy maps of MOF unit cells
# as well as preparation of input files for IPMOF javascript code
# Date: April 2016
# Author: Kutay B. Sezginel

import os
import xlrd
import math
import numpy as np


def energyMap(MOF1, atomList, cutOff, gridSize):
    """
    Calculate energy map for a given MOF class.
    MOF -> base (map) | atomFFparameters -> sigma and epsilon values for given atoms
    cutOff -> cut-off value for LJ potential | gridSize -> grid size array for each dimension
    Packed coordinates for MOF1 must be defined before running the function.
    """
    ucLimit = [math.ceil(MOF1.UCsize[0]), math.ceil(MOF1.UCsize[1]), math.ceil(MOF1.UCsize[2])]

    xGrid = np.linspace(0, ucLimit[0], ucLimit[0]/gridSize+1)
    yGrid = np.linspace(0, ucLimit[1], ucLimit[1]/gridSize+1)
    zGrid = np.linspace(0, ucLimit[2], ucLimit[2]/gridSize+1)

    numAtomsMOF = len(MOF1.uniqueAtomNames)
    numAtomsEnergy = len(atomList['sigma'])

    # Initialize energy map according to grid size and coordinates plus number of unique atoms
    energyMap = np.zeros([len(xGrid)*len(yGrid)*len(zGrid), numAtomsEnergy+3])

    sig, eps = LBmix(MOF1.sigma, atomList['sigma'], MOF1.epsilon, atomList['epsilon'])

    mapIndex = 0
    V = np.zeros([numAtomsEnergy])

    for x in xGrid:
        for y in yGrid:
            for z in zGrid:
                energyMap[mapIndex][0:3] = [x, y, z]
                Vtotal = np.zeros([numAtomsEnergy])
                for unitCell in MOF1.packedCoor:
                    MOF1index = 0
                    for atomCoor in unitCell:
                        atomIndex1 = MOF1.uniqueAtomNames.index(MOF1.atomName[MOF1index])
                        MOF1index += 1
                        r = coorDist(atomCoor, [x, y, z])
                        if r > cutOff:
                            continue
                        if r == 0:
                            energyMap[mapIndex][3:(numAtomsEnergy+3)] = np.ones([1, numAtomsEnergy])*inf
                        else:
                            for atomIndex2 in range(numAtomsEnergy):
                                V[atomIndex2] = calculateLJ(r, sig[atomIndex1][atomIndex2], eps[atomIndex1][atomIndex2])
                                Vtotal[atomIndex2] = Vtotal[atomIndex2] + V[atomIndex2]
                energyMap[mapIndex][3:(numAtomsEnergy+3)] = Vtotal
                mapIndex += 1
    return energyMap


def readMol2(MOFfile):
    """
    Reads mol2 file after opening the file in python and returns unit cell size [a, b, c],
    unit cell angles [alpha, beta, gamma], atom names and atom coordinates [x, y, z]
    """
    lineCount = 0
    readCoordinates = False

    for line in MOFfile:
        if '@<TRIPOS>ATOM' in line:
            readCoordinates = True
            atomName = []
            atomX = []
            atomY = []
            atomZ = []
            atomCoor = []
        if '@<TRIPOS>BOND' in line:
            readCoordinates = False
        if readCoordinates and '@<TRIPOS>ATOM' not in line:
            atomName.append(line.split()[1])
            atomX.append(float(line.split()[2]))
            atomY.append(float(line.split()[3]))
            atomZ.append(float(line.split()[4]))
            atomCoor.append([float(line.split()[2]), float(line.split()[3]), float(line.split()[4])])
        if '@<TRIPOS>CRYSIN' in line:
            lineCount += 1
        if lineCount == 1 and '@<TRIPOS>CRYSIN' not in line:
            a = float(line.split()[0])
            b = float(line.split()[1])
            c = float(line.split()[2])
            alpha = float(line.split()[3])
            beta = float(line.split()[4])
            gamma = float(line.split()[5])
            lineCount += 1

    UCsize = [a, b, c]
    UCangle = [alpha, beta, gamma]
    MOFfile.close()

    return UCsize, UCangle, atomName, atomCoor


# Generates a list of MOF files in given directory with given file format (ex: "".mol2")
def generateMOFlist(fileDir, fileFormat):
    fileList = os.listdir(fileDir)
    MOFlist = []
    for fileName in fileList:
        if fileFormat in fileName:
            MOFlist.append(fileName)
    return MOFlist


# Separates different types of atoms using the atom coordinates and atom names
# Returns unique atom coordinates and unique atoms
def separateAtoms(atomCoor, atomNames):
    uniqueAtoms = []
    for atom in atomNames:
        if atom not in uniqueAtoms:
            uniqueAtoms.append(atom)

    uniqueAtomCoor = [[] for i in range(len(uniqueAtoms))]

    for atomIndex in range(len(atomCoor)):
        uniqueAtomIndex = 0
        for uniqueAtom in uniqueAtoms:
            if atomNames[atomIndex] == uniqueAtom:
                uniqueAtomCoor[uniqueAtomIndex].append(atomCoor[atomIndex])
            uniqueAtomIndex += 1

    return uniqueAtoms, uniqueAtomCoor


# Read force field parameters from an excel file according to force field selection
def readFFparameters(excelFileDir, FFselection):
    # Read Excel File
    forceField_data = xlrd.open_workbook(excelFileDir)
    # Read columns to acquire force field parameters
    atomNames = forceField_data.sheets()[0].col_values(0)[2:]
    UFFsigma = forceField_data.sheets()[0].col_values(1)[2:]
    UFFepsilon = forceField_data.sheets()[0].col_values(2)[2:]
    DREsigma = forceField_data.sheets()[0].col_values(3)[2:]
    DREepsilon = forceField_data.sheets()[0].col_values(4)[2:]
    UFF = [atomNames, UFFsigma, UFFepsilon]
    DRE = [atomNames, DREsigma, DREepsilon]
    if FFselection == 'UFF':
        return UFF
    if FFselection == 'DRE':
        return DRE
    else:
        print('No such force field')


def getFFparameters(atomNames, FFparameters):
    """
    Get force field parameters of the atom list and force field parameters you provide
    """
    atomFFparameters = []
    for atom in atomNames:
        for i in range(len(FFparameters[0])):
            if atom == FFparameters[0][i]:
                atomName = atom
                sigma = FFparameters[1][i]
                epsilon = FFparameters[2][i]
                atomFFparameters.append([atomName, sigma, epsilon])
    return atomFFparameters


def gridBox(p, grid):
    """
    Calculates surrounding grid points for a given point in energy map
    Input x,y,z coordinates of point in space and grid size to get floor and ceiling values
    """
    floor = []
    ceil = []
    index = 0
    for point in p:
        floor.append(math.floor(round(point / grid[index], 1)) * grid[index])
        ceil.append(math.floor(point / grid[index]) * grid[index] + grid[index])
        index += 1
    return floor, ceil


# MOF class that holds coordinate, atom name, and unit cell information
class MOF:
    def initialize(self):
        self.UCsize, self.UCangle, self.atomName, self.atomCoor = readMol2(self.file)
        self.uniqueAtomNames, self.uniqueAtomCoor = separateAtoms(self.atomCoor, self.atomName)

    def initializeFF(self, FFtype):
        FFparam = getFFparameters(self.uniqueAtomNames, FFtype)
        self.sigma = []
        self.epsilon = []
        for i in range(len(FFparam)):
            self.uniqueAtomNames[i] = FFparam[i][0]
            self.sigma.append(FFparam[i][1])
            self.epsilon.append(FFparam[i][2])


# Calculates distance between two given coordinates in list form
def coorDist(coor1, coor2):
    return math.sqrt((coor1[0] - coor2[0])**2 + (coor1[1] - coor2[1])**2 + (coor1[2] - coor2[2])**2)


# Lorentz-Berthelot mixing rules for given lists of sigma1, sigma2, epsilon1, and epsilon2
def LBmix(sigmaList1, sigmaList2, epsilonList1, epsilonList2):
    sig = np.zeros([len(sigmaList1), len(sigmaList2)])
    eps = np.zeros([len(epsilonList1), len(epsilonList2)])

    for index1 in range(len(sigmaList1)):
        for index2 in range(len(sigmaList2)):
            sig[index1][index2] = (sigmaList1[index1] + sigmaList2[index2]) / 2
            eps[index1][index2] = math.sqrt(epsilonList1[index1] * epsilonList2[index2])

    return sig, eps


# Calculate Lennard Jones potential for give distance, sigma, and epsilon values
def calculateLJ(r, sig, eps):
    return 4 * eps * ((sig/r)**12 - (sig/r)**6)


# Packing class containing functions used for packing unit cells
class Packing:

    def factor(UCsize, cutOff):
        packingFactor = []
        for UCdimension in UCsize:
            packingFactor.append(math.ceil(cutOff/UCdimension)*2+1)
        return packingFactor

    def vectors(packingFactor, UCsize, UCangle):

        a = UCsize[0]
        b = UCsize[1]
        c = UCsize[2]
        alpha = math.radians(UCangle[0])
        beta = math.radians(UCangle[1])
        gamma = math.radians(UCangle[2])

        xV = [a, 0, 0]
        yV = [b*math.cos(gamma), b*math.sin(gamma), 0]
        zV = [0.0]*3
        zV[0] = c*math.cos(beta)
        zV[1] = (c*b*math.cos(alpha) - yV[0]*zV[0])/yV[1]
        zV[2] = math.sqrt(c*c - zV[0]*zV[0] - zV[1]*zV[1])

        UCvectors = [xV, yV, zV]

        packingVectors = []
        for x in range(packingFactor[0]):
            for y in range(packingFactor[1]):
                for z in range(packingFactor[2]):
                    packingVectors.append([x, y, z])

        translationVectors = []
        for vector in packingVectors:
            xTranslation = xV[0] * vector[0] + yV[0] * vector[1] + zV[0] * vector[2]
            yTranslation = xV[1] * vector[0] + yV[1] * vector[1] + zV[1] * vector[2]
            zTranslation = xV[2] * vector[0] + yV[2] * vector[1] + zV[2] * vector[2]
            translationVectors.append([xTranslation, yTranslation, zTranslation])

        return translationVectors, UCvectors

    def UC(translationVectors, packingFactors, UCvectors, atomCoor):

        xV = UCvectors[0]
        yV = UCvectors[1]
        zV = UCvectors[2]

        packedCoor = [[] for i in range(len(translationVectors))]

        translationFactor = []
        originTranslationVector = []
        dim = 0
        for factor in packingFactors:
            translationFactor.append((factor-1)/2)
            originTranslationVector.append((factor-1)/2 * xV[dim] + (factor-1)/2 * yV[dim] + (factor-1)/2 * zV[dim])
            dim += 1

        packingIndex = 0
        for translation in translationVectors:
            for coor in atomCoor:
                x = coor[0] + translation[0] - originTranslationVector[0]
                y = coor[1] + translation[1] - originTranslationVector[1]
                z = coor[2] + translation[2] - originTranslationVector[2]
                packedCoor[packingIndex].append([x, y, z])
            packingIndex += 1

        return packedCoor


# Plots atom coordinates for packed unit cells
def plotPackedCell(packedCoor, azim, elev):
    import numpy as np
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt

    from mpl_toolkits.mplot3d import proj3d

    def orthogonal_proj(zfront, zback):
        a = (zfront+zback)/(zfront-zback)
        b = -2*(zfront*zback)/(zfront-zback)
        return np.array([[1, 0, 0, 0],
                        [0, 1, 0, 0],
                        [0, 0, a, b],
                        [0, 0, 0, zback]])
    proj3d.persp_transformation = orthogonal_proj

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    for i in range(len(packedCoor)):
        for coor in packedCoor[i]:
            r = i / len(packedCoor)
            ax.scatter(coor[0], coor[1], coor[2], '-o', c=[r, 0.1, 0.1], s=10)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    ax.azim = azim
    ax.elev = elev

    plt.show()


def plotEnergyMap(eMap, azim, elev):
    import numpy as np
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt

    from mpl_toolkits.mplot3d import proj3d

    def orthogonal_proj(zfront, zback):
        a = (zfront+zback)/(zfront-zback)
        b = -2*(zfront*zback)/(zfront-zback)
        return np.array([[1, 0, 0, 0],
                        [0, 1, 0, 0],
                        [0, 0, a, b],
                        [0, 0, 0, zback]])
    proj3d.persp_transformation = orthogonal_proj

    xCoor = []
    yCoor = []
    zCoor = []
    energy = []
    for i in range(len(eMap)):
        xCoor.append(eMap[i][0])
        yCoor.append(eMap[i][1])
        zCoor.append(eMap[i][2])
        energy.append(eMap[i][3])
    scale = 1E20
    colors = []
    rgb = np.zeros([len(energy), 3])
    for i in range(len(energy)):
        if energy[i] > max(energy)*0.5/scale:
            energy[i] = 1
        elif energy[i] > max(energy)*0.25/scale:
            energy[i] = 0.9
        elif energy[i] > max(energy)*0.1/scale:
            energy[i] = 0.8
        elif energy[i] > max(energy)*0.075/scale:
            energy[i] = 0.7
        elif energy[i] > max(energy)*0.05/scale:
            energy[i] = 0.6
        elif energy[i] > max(energy)*0.025/scale:
            energy[i] = 0.5
        elif energy[i] > max(energy)*0.01/scale:
            energy[i] = 0.4
        else:
            energy[i] = 0.3
        colors.append(energy[i])
        rgb[i][0] = colors[i]

    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_subplot(111, projection='3d')

    ax.scatter(xCoor, yCoor, zCoor, 'o', c=rgb, edgecolor='')

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    ax.azim = azim
    ax.elev = elev

    plt.show()


def exportEnergyMapjs(eMap, exportDir):
    eMapFile = open(exportDir, 'w')
    eMapFile.write("var eMap = [];\n")
    eMapIndex = 0
    for line in eMap:
        eMapFile.write("eMap[" + str(eMapIndex) + "] = ")
        eMapFile.write("[" + str(line[0]) + ", ")
        eMapFile.write(str(line[1]) + ", ")
        eMapFile.write(str(line[2]) + ", ")
        eMapFile.write(str(line[3]) + "];\n")
        eMapIndex += 1
    eMapFile.close()


def exportMOFjs(MOF, exportDir):
    MOFfile = open(exportDir, 'w')
    MOFfile.write("var MOF = [];\n")
    for MOFindex in range(len(MOF.atomName)):
        MOFfile.write("MOF[" + str(MOFindex) + "] = [")
        MOFfile.write(str(MOF.atomCoor[MOFindex][0]) + ", ")
        MOFfile.write(str(MOF.atomCoor[MOFindex][1]) + ", ")
        MOFfile.write(str(MOF.atomCoor[MOFindex][2]) + ", ")
        MOFfile.write("'" + str(MOF.atomName[MOFindex]) + "'" + "];\n")
    MOFfile.close()


# Export coordinates to xyz file
def exportXYZ(packedCoor, atomNames, exportDir):
    xyzFile = open(exportDir, 'w')
    xyzFile.write(str(len(packedCoor)*len(packedCoor[0])))
    xyzFile.write(exportDir.split('/')[-1])
    for UC in packedCoor:
        for atomIndex in range(len(UC)):
            line = atomNames[atomIndex] + ' '
            line += str(UC[atomIndex][0]) + ' '
            line += str(UC[atomIndex][1]) + ' '
            line += str(UC[atomIndex][2]) + ' \n'
            xyzFile.write(line)
    xyzFile.close()
