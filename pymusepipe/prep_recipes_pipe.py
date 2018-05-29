# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""MUSE-PHANGS preparation recipe module
"""

__authors__   = "Eric Emsellem"
__copyright__ = "(c) 2017, ESO + CRAL"
__license__   = "3-clause BSD License"
__contact__   = " <eric.emsellem@eso.org>"

# Importing modules
import os
from os.path import join as joinpath

# Numpy
import numpy as np

# pymusepipe modules
import musepipe as mpipe
from create_sof import SofPipe

# =======================================================
# List of recipes
# =======================================================
list_recipes = ['bias', 'flat', 'wave', 'lsf', 
        'twilight', 'scibasic_all', 'std', 'sky']
        

dic_files_products = {
        'STD': ['DATACUBE_STD', 'STD_FLUXES', 
            'STD_RESPONSE', 'STD_TELLURIC'],
        'TWILIGHT': ['DATACUBE_SKYFLAT', 'TWILIGHT_CUBE'],
        'SKY': ['SKY_SPECTRUM', 'PIXTABLE_REDUCED']
        }
# =======================================================
# Few useful functions
# =======================================================
def add_listpath(suffix, paths) :
    """Add a suffix to a list of path
    and normalise them
    """
    newlist = []
    for mypath in paths:
        newlist.append(mpipe.normpath(joinpath(suffix, mypath)))
    return newlist

def norm_listpath(paths) :
    """Normalise the path for a list of paths
    """
    newlist = []
    for mypath in paths:
        newlist.append(mpipe.normpath(mypath))
    return newlist

###################################################################
# Class for preparing the launch of recipes
###################################################################
class PipePrep(SofPipe) :
    """PipePrep class prepare the SOF files and launch the recipes
    """
    def __init__(self):
        """Initialisation of PipePrep
        """
        SofPipe.__init__(self)
#        super(PipePrep, self).__init__()
        self.list_recipes = list_recipes

    def _get_tpl_meanmjd(self, gtable):
        """Get tpl of the group and mean mjd of the group
        """
        tpl = gtable['tpls'][0]
        mean_mjd = gtable.groups.aggregate(np.mean)['mjd'].data[0]
        return tpl, mean_mjd

    def select_tpl_files(self, expotype=None, tpl="ALL", stage="raw"):
        """Selecting a subset of files from a certain type
        """
        if expotype not in mpipe.listexpo_types.keys() :
            mpipe.print_info("ERROR: input {0} is not in the list of possible values".format(expotype))
            return 

        MUSE_subtable = self._get_table_expo(expotype, stage)
        if len(MUSE_subtable) == 0:
            if self.verbose :
                mpipe.print_warning("Empty file table of type {0}".format(expotype))
                mpipe.print_warning("Returning an empty Table from the tpl -astropy- selection")
            return MUSE_subtable

        group_table = MUSE_subtable.group_by('tpls')
        if tpl == "ALL":
            return group_table
        else :
            return group_table.groups[group_table.groups.key['tpls'] == tpl]
        
    def run_all_recipes(self, fraction=0.8):
        """Running all recipes in one shot
        """
        self.run_bias()
        self.run_flat()
        self.run_wave()
        self.run_lsf()
        self.run_twilight()
        self.run_scibasic_all()
        self.run_std()
        self.run_sky(fraction=fraction)

    def run_bias(self, sof_filename='bias', tpl="ALL"):
        """Reducing the Bias files and creating a Master Bias
        Will run the esorex muse_bias command on all Biases

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        tpl_gtable = self.select_tpl_files(expotype='BIAS', tpl=tpl)
        if len(tpl_gtable) == 0:
            if self.verbose :
                mpipe.print_warning("No BIAS recovered from the astropy Table - Aborting")
                return
        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the BIASES including
        # the list of files to be processed for one MASTER BIAS
        # Adding the bad pixel table
        self._add_calib_to_sofdict("BADPIX_TABLE", reset=True)
        for gtable in tpl_gtable.groups:
            # Provide the list of files to the dictionary
            self._sofdict['BIAS'] = add_listpath(self.paths.rawfiles,
                    gtable['filename'].data.astype(np.object))
            # extract the tpl (string)
            tpl = gtable['tpls'][0]
            # Writing the sof file
            self.write_sof(sof_filename=sof_filename + "_" + tpl, new=True)
            # Name of final Master Bias
            name_bias = self._get_suffix_expo('BIAS')
            dir_bias = self._get_fullpath_expo('BIAS', "master")
            # Run the recipe
            self.recipe_bias(self.current_sof, dir_bias, name_bias, tpl)

        # Write the MASTER BIAS Table and save it
        self.save_expo_table('BIAS', tpl_gtable, "master")

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

    def run_flat(self, sof_filename='flat', tpl="ALL"):
        """Reducing the Flat files and creating a Master Flat
        Will run the esorex muse_flat command on all Flats

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        tpl_gtable = self.select_tpl_files(expotype='FLAT', tpl=tpl)
        if len(tpl_gtable) == 0:
            if self.verbose :
                mpipe.print_warning("No FLAT recovered from the astropy Table - Aborting")
                return

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the FLATs including
        # the list of files to be processed for one MASTER Flat
        # Adding the bad pixel table
        self._add_calib_to_sofdict("BADPIX_TABLE", reset=True)
        for gtable in tpl_gtable.groups:
            # Provide the list of files to the dictionary
            self._sofdict['FLAT'] = add_listpath(self.paths.rawfiles,
                    gtable['filename'].data.astype(np.object))
            # extract the tpl (string) and mean mjd (float) 
            tpl, mean_mjd = self._get_tpl_meanmjd(gtable)
            # Adding the best tpc MASTER_BIAS
            self._add_tplmaster_to_sofdict(mean_mjd, 'BIAS')
            # Writing the sof file
            self.write_sof(sof_filename=sof_filename + "_" + tpl, new=True)
            # Name of final Master Flat and Trace Table
            dir_flat = self._get_fullpath_expo('FLAT', "master")
            name_flat =  self._get_suffix_expo('FLAT')

            dir_trace = self._get_fullpath_expo('TRACE', "master")
            name_tracetable = self._get_suffix_expo('TRACE')
            # Run the recipe
            self.recipe_flat(self.current_sof, dir_flat, name_flat, dir_trace, name_tracetable, tpl)

        # Write the MASTER FLAT Table and save it
        self.save_expo_table('FLAT', tpl_gtable, "master")
        self.save_expo_table('TRACE', tpl_gtable, "master")

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

    def run_wave(self, sof_filename='wave', tpl="ALL"):
        """Reducing the WAVE-CAL files and creating the Master Wave
        Will run the esorex muse_wave command on all Flats

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        tpl_gtable = self.select_tpl_files(expotype='WAVE', tpl=tpl)
        if len(tpl_gtable) == 0:
            if self.verbose :
                mpipe.print_warning("No WAVE recovered from the astropy file Table - Aborting")
                return

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the FLATs including
        # the list of files to be processed for one WAVECAL
        # Adding Badpix table and Line Catalog
        self._add_calib_to_sofdict("BADPIX_TABLE", reset=True)
        self._add_calib_to_sofdict("LINE_CATALOG")
        for gtable in tpl_gtable.groups:
            # Provide the list of files to the dictionary
            self._sofdict['ARC'] = add_listpath(self.paths.rawfiles,
                    gtable['filename'].data.astype(np.object))
            # extract the tpl (string) and mean mjd (float) 
            tpl, mean_mjd = self._get_tpl_meanmjd(gtable)
            # Finding the best tpl for BIAS + TRACE
            self._add_list_tplmaster_to_sofdict(mean_mjd, ['BIAS', 'TRACE'])
            # Writing the sof file
            self.write_sof(sof_filename=sof_filename + "_" + tpl, new=True)
            # Name of final Master Wave
            dir_wave = self._get_fullpath_expo('WAVE', "master")
            name_wave = self._get_suffix_expo('WAVE')
            # Run the recipe
            self.recipe_wave(self.current_sof, dir_wave, name_wave, tpl)

        # Write the MASTER WAVE Table and save it
        self.save_expo_table('WAVE', tpl_gtable, "master")

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

    def run_lsf(self, sof_filename='lsf', tpl="ALL"):
        """Reducing the LSF files and creating the LSF PROFILE
        Will run the esorex muse_lsf command on all Flats

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        tpl_gtable = self.select_tpl_files(expotype='WAVE', tpl=tpl)
        if len(tpl_gtable) == 0:
            if self.verbose :
                mpipe.print_warning("No WAVE recovered from the astropy file Table - Aborting")
                return

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the LSF including
        # the list of files to be processed for one MASTER Flat
        # Adding Badpix table and Line Catalog
        self._add_calib_to_sofdict("BADPIX_TABLE", reset=True)
        self._add_calib_to_sofdict("LINE_CATALOG")
        for gtable in tpl_gtable.groups:
            # Provide the list of files to the dictionary
            self._sofdict['ARC'] = add_listpath(self.paths.rawfiles,
                    gtable['filename'].data.astype(np.object))
            # extract the tpl (string) and mean mjd (float) 
            tpl, mean_mjd = self._get_tpl_meanmjd(gtable)
            # Finding the best tpl for BIAS, TRACE, WAVE
            self._add_list_tplmaster_to_sofdict(mean_mjd, ['BIAS', 'TRACE', 'WAVE'])
            # Writing the sof file
            self.write_sof(sof_filename=sof_filename + "_" + tpl, new=True)
            # Name of final Master Wave
            dir_lsf = self._get_fullpath_expo('LSF', "master")
            name_lsf = self._get_suffix_expo('LSF')
            # Run the recipe
            self.recipe_lsf(self.current_sof, dir_lsf, name_lsf, tpl)

        # Write the MASTER LSF PROFILE Table and save it
        self.save_expo_table('LSF', tpl_gtable, "master")

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

    def run_twilight(self, sof_filename='twilight', tpl="ALL"):
        """Reducing the  files and creating the TWILIGHT CUBE.
        Will run the esorex muse_twilight command on all TWILIGHT

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        tpl_gtable = self.select_tpl_files(expotype='TWILIGHT', tpl=tpl)
        if len(tpl_gtable) == 0:
            if self.verbose :
                mpipe.print_warning("No TWILIGHT recovered from the astropy file Table - Aborting")
                return

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the LSF including
        # the list of files to be processed for one MASTER Flat
        self._add_calib_to_sofdict("BADPIX_TABLE", reset=True)
        self._add_calib_to_sofdict("VIGNETTING_MASK")
        for gtable in tpl_gtable.groups:
            # extract the tpl (string) and mean mjd (float) 
            tpl, mean_mjd = self._get_tpl_meanmjd(gtable)
            self._add_geometry_to_sofdict(tpl)
            # Provide the list of files to the dictionary
            self._sofdict['TWILIGHT'] = add_listpath(self.paths.rawfiles,
                    gtable['filename'].data.astype(np.object))
            # Finding the best tpl for BIAS, ILLUM, FLAT, TRACE, WAVE
            self._add_tplraw_to_sofdict(mean_mjd, "ILLUM")
            self._add_list_tplmaster_to_sofdict(mean_mjd, ['BIAS', 'FLAT', 'TRACE', 'WAVE'])
            # Writing the sof file
            self.write_sof(sof_filename=sof_filename + "_" + tpl, new=True)
            # Names and folder of final Master Wave
            name_products = dic_files_products['TWILIGHT']
            dir_twilight = self._get_fullpath_expo('TWILIGHT', "master")
            name_twilight = self._get_suffix_expo('TWILIGHT')
            self.recipe_twilight(self.current_sof, dir_twilight, name_twilight, name_products, tpl)

        # Write the MASTER TWILIGHT Table and save it
        self.save_expo_table('TWILIGHT', tpl_gtable, "master")

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

    def run_scibasic_all(self, list_object=['OBJECT', 'SKY', 'STD'], tpl="ALL"):
        """Running scibasic for all objects in list_object
        Making different sof for each category
        """
        for expotype in list_object:
            sof_filename = 'scibasic_{0}'.format(expotype.lower())
            self.run_scibasic(sof_filename=sof_filename, expotype=expotype, tpl=tpl)

    def run_scibasic(self, sof_filename='scibasic', expotype="OBJECT", tpl="ALL"):
        """Reducing the files of a certain category and creating the PIXTABLES
        Will run the esorex muse_scibasic 

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        tpl_gtable = self.select_tpl_files(expotype=expotype, tpl=tpl)
        if len(tpl_gtable) == 0:
            if self.verbose :
                mpipe.print_warning("No {0} recovered from the astropy file Table - Aborting".format(expotype))
                return

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the LSF including
        # the list of files to be processed for one MASTER Flat
        for gtable in tpl_gtable.groups:
            self._add_calib_to_sofdict("BADPIX_TABLE", reset=True)
            self._add_calib_to_sofdict("LINE_CATALOG")
            # extract the tpl (string) and mean mjd (float) 
            tpl, mean_mjd = self._get_tpl_meanmjd(gtable)
            self._add_geometry_to_sofdict(tpl)
            # Provide the list of files to the dictionary
            self._sofdict[expotype] = add_listpath(self.paths.rawfiles,
                    gtable['filename'].data.astype(np.object))
            # Number of objects
            Nexpo = len(self._sofdict[expotype])
            if self.verbose:
                mpipe.print_info("Number of expo is {Nexpo} for {expotype}".format(Nexpo=Nexpo, expotype=expotype))
            # Finding the best tpl for BIAS
            self._add_tplraw_to_sofdict(mean_mjd, "ILLUM") 
            self._add_list_tplmaster_to_sofdict(mean_mjd, ['BIAS', 'FLAT', 
                'TRACE', 'WAVE', 'TWILIGHT'])
            # Writing the sof file
            self.write_sof(sof_filename=sof_filename + "_" + tpl, new=True)
            # Run the recipe to reduce the standard (muse_scibasic)

            dir_products = self._get_fullpath_expo(expotype, "processed")
            suffix = self._get_suffix_expo(expotype)
            name_products = []
            for i in range(Nexpo):
                name_products += ['{0}_{1:04d}-{2:02d}.fits'.format(suffix, i+1, j+1) for j in range(24)]
            self.recipe_scibasic(self.current_sof, tpl, expotype, dir_products, name_products)

        # Write the MASTER files Table and save it
        self.save_expo_table(expotype, tpl_gtable, "processed")

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

    def run_std(self, sof_filename='standard', tpl="ALL"):
        """Reducing the STD files after they have been obtained
        Running the muse_standard routine

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        std_table = self.select_tpl_files("STD", tpl=tpl, stage="processed")
        if len(std_table) == 0:
            if self.verbose :
                mpipe.print_warning("No processed STD recovered from the astropy file Table - Aborting")
                return

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the STD Sof
        for i in range(len(std_table)):
            mytpl = std_table['tpls'][i]
            if tpl != "ALL" and tpl != mytpl :
                continue
            # Now starting with the standard recipe
            self._add_calib_to_sofdict("EXTINCT_TABLE", reset=True)
            self._add_calib_to_sofdict("STD_FLUX_TABLE")
            self._sofdict['PIXTABLE_STD'] = [joinpath(self._get_fullpath_expo("STD", "processed"),
                'PIXTABLE_STD_{0}-{1:02d}.fits'.format(mytpl, j+1)) for j in range(24)]
            self.write_sof(sof_filename=sof_filename + "_" + mytpl, new=True)
            name_std = dic_files_products['STD']
            dir_std = self._get_fullpath_expo('STD', "master")
            self.recipe_std(self.current_sof, dir_std, name_std, mytpl)

        # Write the MASTER files Table and save it
        self.save_expo_table("STD", std_table, "master")

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

    def run_sky(self, sof_filename='sky', tpl="ALL", fraction=0.8):
        """Reducing the SKY after they have been scibasic reduced
        Will run the esorex muse_create_sky routine

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time

        """
        # First selecting the files via the grouped table
        sky_table = self._get_table_expo("SKY", "raw")
        if len(sky_table) == 0:
            if self.verbose :
                mpipe.print_warning("No SKY recovered from the astropy file Table - Aborting")
                return

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for the LSF including
        # the list of files to be processed for one MASTER Flat
        for i in range(len(sky_table)):
            mytpl = sky_table['tpls'][i]
            mymjd = sky_table['mjd'][i]
            if tpl != "ALL" and tpl != mytpl :
                continue
            # Now starting with the standard recipe
            self._add_calib_to_sofdict("EXTINCT_TABLE", reset=True)
            self._add_calib_to_sofdict("SKY_LINES")
            self._add_skycalib_to_sofdict("STD_RESPONSE", mymjd, 'STD')
            self._add_skycalib_to_sofdict("STD_TELLURIC", mymjd, 'STD')
            self._add_tplmaster_to_sofdict(mymjd, 'LSF')
            self._sofdict['PIXTABLE_SKY'] = [joinpath(self._get_fullpath_expo("SKY", "processed"),
                'PIXTABLE_SKY_{0:04d}-{1:02d}.fits'.format(i+1,j+1)) for j in range(24)]
            self.write_sof(sof_filename=sof_filename + "{0:02d}".format(i+1) + "_" + mytpl, new=True)
            dir_sky = self._get_fullpath_expo('SKY', "processed")
            name_sky = dic_files_products['SKY']
            self.recipe_sky(self.current_sof, dir_sky, name_sky, mytpl, fraction=fraction)

        # Go back to original folder
        self.goto_prevfolder(logfile=True)

################### OLD ############################################
#    def create_calibrations(self):
#        self.check_for_calibrations()
#        # MdB: this creates the standard calibrations, if needed
#        if not ((self.redo==0) and (self.Master['BIAS']==1)):
#            self.run_bias()
#        if not ((self.redo==0) and (self.Master['DARK']==1)):
#            self.run_dark()
#        if not ((self.redo==0) and (self.Master['FLAT']==1)):
#            self.run_flat()
#        if not ((self.redo==0) and (self.Master['WAVE']==1)):
#            self.run_wavecal()
#        if not ((self.redo==0) and (self.Master['TWILIGHT']==1)):
#            self.run_twilight()    
#        if not ((self.redo==0) and (self.Master['STD']==1)):
#            self.create_standard_star()
#            self.run_standard_int()
#
#    def check_for_calibrations(self, verbose=None):
#        """This function checks which calibration file are present, just in case
#        you do not wish to redo them. Variables are named: 
#        masterbias, masterdark, standard, masterflat, mastertwilight
#        """
#        
#        outcal = getattr(self.my_params, "master" + suffix_folder)
#        if verbose is None: verbose = self.verbose
#
#        for mastertype in dic_listMaster.keys() :
#            [fout, suffix] = dic_listMaster[mastertype]
#            # If TWILIGHT = only one cube
#            if mastertype == "TWILIGHT" :
#                if not os.path.isfile(joinpath(outcal, fout, "{suffix}.fits".format(suffix=suffix))):
#                    self.Master[mastertype] = False
#
#                if verbose :
#                    if self.Master[mastertype] :
#                        print("WARNING: Twilight flats already made")
#                    else :
#                        print("WARNING: Twilight flats NOT there yet")
#
#            # Others = 24 IFU exposures
#            else :
#                for ifu in range(1,25):
#                    if not os.path.isfile(joinpath(outcal, fout, "{0}-{1:02d}.fits".format(suffix, ifu))):
#                        self.Master[mastertype] = False
#                        break
#                if verbose :
#                    if self.Master[mastertype]:
#                        print("WARNING: Master {0} already in place".format(mastertype))
#                    else :
#                        print("WARNING: Master {0} NOT yet there".format(mastertype))
#
