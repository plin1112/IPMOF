# IPMOF Crystal Functions
# Date: June 2016
# Author: Kutay B. Sezginel
import math
import os
from forcefield import get_ff_parameters


class MOF:
    """
    MOF class that holds coordinate, atom name, and unit cell information
    """
    def initialize(self):
        """
        Initialize MOF name, unit cell volume and parameters, atom names and coordinates, and
        unique atom names and coordinates by reading values from mol2 file.
        """
        self.uc_size, self.uc_angle, self.atom_names, self.atom_coors = read_mol2(self.mol2_path)
        self.uniq_atom_names, self.uniq_atom_coors = separate_atoms(self.atom_coors, self.atom_names)
        self.ucv, self.frac_ucv = unit_cell_volume(self.uc_size, self.uc_angle)
        self.name = os.path.split(self.mol2_path)[-1].split('.')[0]

    def initialize_ff(self, ff_type):
        """
        Initialzes force field parameters according to unique atom names.
        """
        ff_param = get_ff_parameters(self.uniq_atom_names, ff_type)
        self.sigma = []
        self.epsilon = []
        for i in range(len(ff_param)):
            self.uniq_atom_names[i] = ff_param[i][0]
            self.sigma.append(ff_param[i][1])
            self.epsilon.append(ff_param[i][2])

    def __len__(self):
        return len(self.atom_coors)


def read_mol2(mof_mol2_path):
    """
    Reads mol2 file after opening the file in python and returns unit cell size [a, b, c],
    unit cell angles [alpha, beta, gamma], atom names and atom coordinates [x, y, z]
    """
    mol2_file = open(mof_mol2_path, 'r')
    mol2_lines = mol2_file.readlines()
    mol2_file.close()

    line_count = 0
    read_coor = False

    for line in mol2_lines:
        if '@<TRIPOS>ATOM' in line:
            read_coor = True
            atom_names = []
            atom_coors = []
        if '@<TRIPOS>BOND' in line:
            read_coor = False
        if read_coor and '@<TRIPOS>ATOM' not in line:
            name = line.split()[1]
            for char_index, char in enumerate(name):
                if char.isdigit():
                    name = name[:char_index]
                elif char == '(':
                    name = name[:char_index]
            atom_names.append(name)
            atom_x = float(line.split()[2])
            atom_y = float(line.split()[3])
            atom_z = float(line.split()[4])
            atom_coors.append([atom_x, atom_y, atom_z])
        if '@<TRIPOS>CRYSIN' in line:
            line_count += 1
        if line_count == 1 and '@<TRIPOS>CRYSIN' not in line:
            a = float(line.split()[0])
            b = float(line.split()[1])
            c = float(line.split()[2])
            alpha = float(line.split()[3])
            beta = float(line.split()[4])
            gamma = float(line.split()[5])
            line_count += 1

    uc_size = [a, b, c]
    uc_angle = [alpha, beta, gamma]

    return uc_size, uc_angle, atom_names, atom_coors


def separate_atoms(atom_coors, atom_names):
    """
    Identifies different types of atoms in given atom coordinates and atom names
    Returns unique atom coordinates and unique atom names
    """
    uniq_atom_names = []
    for atom in atom_names:
        if atom not in uniq_atom_names:
            uniq_atom_names.append(atom)

    uniq_atom_coors = [[] for i in range(len(uniq_atom_names))]
    for atom_index in range(len(atom_coors)):
        for uniq_atom_index, uniq_atom in enumerate(uniq_atom_names):
            if atom_names[atom_index] == uniq_atom:
                uniq_atom_coors[uniq_atom_index].append(atom_coors[atom_index])

    return uniq_atom_names, uniq_atom_coors


class Packing:
    """
    Packing class containing functions used for packing unit cells
    """
    def factor(uc_size, cut_off):
        """
        Calculate packing factor for given unit cell size and cut off radius
        """
        packing_factor = []
        for uc_length in uc_size:
            packing_factor.append(math.ceil(cut_off / uc_length) * 2 + 1)
        return packing_factor

    def uc_vectors(uc_size, uc_angle):
        """
        Calculate unit cell vectors for given unit cell size and angles
        """
        a = uc_size[0]
        b = uc_size[1]
        c = uc_size[2]
        alpha = math.radians(uc_angle[0])
        beta = math.radians(uc_angle[1])
        gamma = math.radians(uc_angle[2])

        x_v = [a, 0, 0]
        y_v = [b * math.cos(gamma), b * math.sin(gamma), 0]
        z_v = [0.0] * 3
        z_v[0] = c * math.cos(beta)
        z_v[1] = (c * b * math.cos(alpha) - y_v[0] * z_v[0]) / y_v[1]
        z_v[2] = math.sqrt(c * c - z_v[0] * z_v[0] - z_v[1] * z_v[1])
        uc_vectors = [x_v, y_v, z_v]
        return uc_vectors

    def translation_vectors(packing_factor, uc_vectors):
        """
        Calculate translation vectors for given packing factor and uc vectors
        """
        packing_amount = []
        for x in range(packing_factor[0]):
            for y in range(packing_factor[1]):
                for z in range(packing_factor[2]):
                    packing_amount.append([x, y, z])

        x_v = uc_vectors[0]
        y_v = uc_vectors[1]
        z_v = uc_vectors[2]
        translation_vectors = []
        for pack in packing_amount:
            x_trans = x_v[0] * pack[0] + y_v[0] * pack[1] + z_v[0] * pack[2]
            y_trans = x_v[1] * pack[0] + y_v[1] * pack[1] + z_v[1] * pack[2]
            z_trans = x_v[2] * pack[0] + y_v[2] * pack[1] + z_v[2] * pack[2]
            translation_vectors.append([x_trans, y_trans, z_trans])

        return translation_vectors

    def uc_coors(translation_vectors, packing_factors, uc_vectors, atom_coors):
        """
        Calculate packed coordinates for given:
        - translation vectors  - packing factor     - unit cell vectors    - atom coordinates
        """
        x_v = uc_vectors[0]
        y_v = uc_vectors[1]
        z_v = uc_vectors[2]

        packed_coors = [[] for i in range(len(translation_vectors))]
        translation_factor = []
        origin_trans_vec = []
        for dim, factor in enumerate(packing_factors):
            translation_factor.append((factor - 1) / 2)
            origin_translation = (factor - 1) / 2 * x_v[dim] + (factor - 1) / 2 * y_v[dim]
            origin_translation += (factor - 1) / 2 * z_v[dim]
            origin_trans_vec.append(origin_translation)

        packing_index = 0
        for translation in translation_vectors:
            for coor in atom_coors:
                x = coor[0] + translation[0] - origin_trans_vec[0]
                y = coor[1] + translation[1] - origin_trans_vec[1]
                z = coor[2] + translation[2] - origin_trans_vec[2]
                packed_coors[packing_index].append([x, y, z])
            packing_index += 1

        return packed_coors

    def edge_points(uc_vectors):
        """
        Calculate coordinates of unit cell edges in order of:
        (0, 0, 0) - (a, 0, 0) - (b, 0, 0) - (c, 0, 0)
        (a, b, 0) - (0, b, c) - (a, 0, c) - (a, b, c)
        """
        uc_edges = []
        uc_edges.append([0, 0, 0])

        # (a, 0, 0) - (b, 0, 0) - (c, 0, 0)
        for vec in uc_vectors:
            uc_edges.append(vec)

        # (a, b, 0)
        uc_edges.append([uc_vectors[0][0] + uc_vectors[1][0], uc_vectors[0][1] + uc_vectors[1][1],
                        uc_vectors[0][2] + uc_vectors[1][2]])
        # (0, b, c)
        uc_edges.append([uc_vectors[1][0] + uc_vectors[2][0], uc_vectors[1][1] + uc_vectors[2][1],
                        uc_vectors[1][2] + uc_vectors[2][2]])
        # (a, 0, c)
        uc_edges.append([uc_vectors[0][0] + uc_vectors[2][0], uc_vectors[0][1] + uc_vectors[2][1],
                        uc_vectors[0][2] + uc_vectors[2][2]])
        # (a, b, c)
        uc_edges.append([uc_vectors[0][0] + uc_vectors[1][0] + uc_vectors[2][0],
                        uc_vectors[0][1] + uc_vectors[1][1] + uc_vectors[2][1],
                        uc_vectors[0][2] + uc_vectors[1][2] + uc_vectors[2][2]])
        return uc_edges


def unit_cell_volume(uc_size, uc_angle):
    """
    Calculates unit cell volume of a given MOF object.
    """
    a = uc_size[0]
    b = uc_size[1]
    c = uc_size[2]
    alp = math.radians(uc_angle[0])
    bet = math.radians(uc_angle[1])
    gam = math.radians(uc_angle[2])

    volume = 1 - math.cos(alp)**2 - math.cos(bet)**2 - math.cos(gam)**2
    volume += 2 * math.cos(alp) * math.cos(bet) * math.cos(gam)
    volume = a * b * c * math.sqrt(volume)
    frac_volume = volume / (a * b * c)

    return volume, frac_volume


def calculate_cut_off(MOF):
    """"
    Calculate cut-off radius as Rc = L/2 from a given MOF object.
    """
    width_a = MOF.ucv / (MOF.uc_size[1] * MOF.uc_size[2] / math.sin(math.radians(MOF.uc_angle[0])))
    width_b = MOF.ucv / (MOF.uc_size[0] * MOF.uc_size[2] / math.sin(math.radians(MOF.uc_angle[1])))
    width_c = MOF.ucv / (MOF.uc_size[0] * MOF.uc_size[1] / math.sin(math.radians(MOF.uc_angle[2])))
    MOF.cut_off = min(width_a / 2, width_b / 2, width_c / 2)

    return MOF.cut_off


def export_xyz(atom_coors, atom_names, file_name, export_dir):
    """
    Export given atom coordinates and names in .xyz format.

    Example usage:
     >>> export_xyz(MOF.atom_coors, MOF.atom_names. MOF.name, export_dir)
    """
    xyz_dir = os.path.join(export_dir, file_name + '.xyz')
    xyz_file = open(xyz_dir, 'w')
    xyz_file.write(str(len(atom_coors)) + '\n')
    xyz_file.write(file_name + '\n')

    for atom, coor in zip(atom_names, atom_coors):
        xyz_file.write(atom + ' ' + str(coor[0]) + ' ' + str(coor[1]) + ' ' + str(coor[2]) + '\n')
    xyz_file.close()