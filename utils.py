import requests
from bs4 import BeautifulSoup
import bs4
import pandas as pd
import os
from pandas.api.types import is_numeric_dtype

class Plant_Table:
    """
        url: url of the wikipedia page
        col_names: list of column names to be used for the dataframe
        del_df: list of indices of tables to be deleted from the dataframe
        del_cols: list of columns to be deleted from the dataframe
        merges: list of tuples of two elements, where the first element is the name of the new column and the second and third elements are the names of the columns to be merged
        unmerge: list of ['column_name_to_be_unmerged', 'new_column_name', 'new_column_name', 'delimiter1', 'delimiter2']
        """
    def __init__(self, url: str="", col_names: list="", del_df: list=[], del_cols: list=[], merges: list=[], unmerge=[]):
        
        self.ext = ".csv"
        self.remove_list = ["many types","[", "]", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "\"" , "\'", "(", ")", ":", ";", "!", "citation needed", "including", " good ", " coupled ", " with ", " seems ", " to ", " encourage ", 'its flowers', "it's flowers", ' cleome ', ' together ', 'traps various', ' other ', ' is ', ' a ', ' a legume ', ' fertile ', ' too ', ' and ', ' the ', 'traps ','european',' attract ', ' in ', ' of ', ' almost ', ' to ', ' with ', ' on ', ' at ', ' by ', ' everything ', 'almost ', 'etc.','most ', 'especially', ' etc','relatives']
        self.replace_with = [('its flowers attract', ''),('other ', ''), ('almost ', ''), ('nightshades ', 'nightshades,'), ('cucurbits ', 'cucurbits,'), ('/', ','), (' of ', ' '), ('a variety ', ' '), (' variety ', ' '), (' many ', ' '), ('repels ', ''), ('imported ', ''), ('beetle ', 'beetle,'), ('beetles ', 'beetles,'), ('insects', 'insects,'), ('citation needed', ''), (' and ', ','), (' everything',',everything'), (' predatory',',predatory'),('etc.',''),('e.g.',''),('&',','),('onions ','onions,'),('.',',')]
        self.delete_words_if_alone = ["", '', 'many','relatives']

        if not os.path.exists('data\companion_plants.csv'):
            assert url != "", "url cannot be empty"
            self.get_wiki_table(url, col_names, del_df, del_cols, merges, unmerge)
        else:
            self.df = pd.read_csv('data\companion_plants.csv')

    def get_compatible(self, plant:str, strict:int=1):
        """Recursively finds the compatible plants for the given plant"""
        assert strict in ['strictly_intercompatible', 'moderately_intercompatible', 'simple'], "strict must be 'strictly_intercompatible', 'moderately_intercompatible' or 'simple'"

        compatible = self.helped_by(plant) + self.helps(plant)
        incompatible = self.incompatible(plant)
        if strict == 'simple':
            return compatible

        compatible = list(set(compatible) - set(incompatible))

        if strict == 'moderately_intercompatible':
            return compatible
        
        all_incompatible = [self.incompatible(plant) for plant in compatible]
        all_incompatible = list(set([item for sublist in all_incompatible for item in sublist]))
        compatible = list(set(compatible) - set(all_incompatible))
        compatible = sorted(compatible)

        return compatible

    def get_compatible_groups(self, plant, strict:str='strictly_intercompatible', print_groups:bool=False):
        """Get groups of compatible plants from among the given plants. Given a plant, finds inter-compatible plants from among the given plants
        
        strict: 'strictly_intercompatible', 'moderately_intercompatible' or 'intercompatible'
        print_groups: if True, prints the groups of compatible plants
        plant: the plant for which the compatible plants are to be found
        
        returns: list of lists of inter_compatible plants"""
        assert strict in ['strictly_intercompatible', 'moderately_intercompatible', 'simple'], "strict must be 'strictly_intercompatible', 'moderately_intercompatible' or 'simple'"
        plants = self.get_compatible(plant, strict=strict)
        inc_dict = {plant:self.incompatible(plant) for plant in plants + [plant]}
        
        # ensure that the plant is not in the incompatible list of any other plant
        possible_groups = []
        for plant in plants:
            possible_groups.append([plant])
            
            for next_plant in plants:
                if plant != next_plant:
                    all_inc = [inc_dict[plant1] for plant1 in possible_groups[-1]] + [inc_dict[next_plant]] + [inc_dict[plant]]
                    all_inc = list(set([item for sublist in all_inc for item in sublist]))
                    if next_plant not in all_inc:
                        compatible = self.get_compatible(next_plant, strict=strict)

                        if strict == 'strictly_intercompatible':
                            if all([plant1 in compatible for plant1 in possible_groups[-1]]):
                                possible_groups[-1].append(next_plant)
                        elif strict == 'moderately_intercompatible':
                            if all([plant1 in compatible for plant1 in possible_groups[-1]]):
                                possible_groups[-1].append(next_plant)
                        else:
                            possible_groups[-1].append(next_plant)

        # sort
        for i in range(len(possible_groups)):
            possible_groups[i] = sorted(possible_groups[i])

        possible_groups = [list(x) for x in set(tuple(x) for x in possible_groups)]

        # remove lists which are subsets of other lists
        possible_groups = [group for group in possible_groups if not any([set(group).issubset(set(group1)) for group1 in possible_groups if group != group1])]
            
        if print_groups:
            for group in possible_groups:
                print(group)
        return possible_groups
        
    def incompatible(self, plant:str):
        """Finds the incompatible plants for the given plant"""
        incompatible = self.avoid(plant)
        if incompatible == []:
            return []
        return incompatible
        
    def helped_by(self, plant:str):
        # the names of the plants that the plant helps
        helped_by_index = self.df['names'].loc[self.df['names'].str.contains(plant, case=False)].index
        if len(helped_by_index) == 0:
            return []
        helped_by = self.df.iloc[helped_by_index]['helped by'].values[0]
        return self.str_rep_of_list_to_list(helped_by)

    def helps(self, plant:str):
        # the names of the plants that the plant helps
        helps_index = self.df['names'].loc[self.df['names'].str.contains(plant, case=False)].index
        if len(helps_index) == 0:
            return []
        helps = self.df.iloc[helps_index]['helps'].values[0]
        return self.str_rep_of_list_to_list(helps)

    def get_plant_names(self):
        names = [self.str_rep_of_list_to_list(x ) for x in self.df['names']]
        # get the 1) shortest name 2) if it had the fewest spaces
        simple_names = set()
        for l in names:
            if len (l) == 0:
                continue
            if len(l) > 1:
                l_add = [x for x in l if len(x) > 1]
                # find the shortest name
                l_add = sorted(l_add, key=len)
                l_add = [x for x in l_add if len(x) == len(l_add[0])]
                # find the name with the fewest spaces
                l_add = sorted(l_add, key=lambda x: x.count(' '))
                l_add = [x for x in l_add if x.count(' ') == l_add[0].count(' ')]
                simple_names.add(l_add[0])
            elif len(l[0]) > 1:
                    simple_names.add(l[0])
        # to list
        simple_names = [x for x in simple_names if x not in ['nan', '', 'various']]
        return  simple_names

    def attracts_hosts(self, plant:str):
        # the names of the plants that the plant helps
        attracts_hosts_index = self.df['names'].loc[self.df['names'].str.contains(plant, case=False)].index
        if len(attracts_hosts_index) == 0:
            return []
        attracts_hosts = self.df.iloc[attracts_hosts_index]['attracts/hosts'].values[0]
        return self.str_rep_of_list_to_list(attracts_hosts )

    def repels_traps(self, plant:str):
        # the names of the plants that the plant helps
        repels_traps_index = self.df['names'].loc[self.df['names'].str.contains(plant, case=False)].index
        if len(repels_traps_index) == 0:
            return []
        repels_traps = self.df.iloc[repels_traps_index]['repels/traps'].values[0]
        return self.str_rep_of_list_to_list(repels_traps)

    def attracts(self, plant:str):
        # the names of the plants that the plant helps
        attracts_index = self.df['names'].loc[self.df['names'].str.contains(plant, case=False)].index
        if len(attracts_index) == 0:
            return []
        attracts = self.df.iloc[attracts_index]['attracts'].values[0]
        return self.str_rep_of_list_to_list(attracts)

    def avoid(self, plant:str):
        # the names of the plants that the plant helps
        avoid_index = self.df['names'].loc[self.df['names'].str.contains(plant, case=False)].index
        if len(avoid_index) == 0:
            return []
        avoid = self.df.iloc[avoid_index]['avoid'].values[0]
        return self.str_rep_of_list_to_list(avoid)

    def str_rep_of_list_to_list(self, string:str):
        string = list(set(string.replace("[", "").replace("]", "").replace(" ", "").replace("\'", "").replace("""\'""","").replace("\"", "").split(",")))
        string = [x for x in string if x != ""]
        return string

    def get_wiki_table(self, url: str, col_names: list = None, del_df: list=[], del_cols: list=[], merges: list=[], unmerge=[]):
        """
        url: url of the wikipedia page
        col_names: list of column names to be used for the dataframe
        del_df: list of indices of tables to be deleted from the dataframe
        del_cols: list of columns to be deleted from the dataframe
        merges: list of tuples of two elements, where the first element is the name of the new column and the second and third elements are the names of the columns to be merged
        unmerge: list of ['column_name_to_be_unmerged', 'new_column_name', 'new_column_name', 'delimiter1', 'delimiter2']
        """
        # any tuple of two in col_names represents a request for a column merge, while single elements are just column names to be renamed
        self.merges = merges
        self.unmerge = unmerge
        self.col_names = col_names
        self.companion_table = pd.read_html(url)
        self.url = url
        self.col_names = col_names
        self.del_df = del_df
        self.length = len(self.companion_table)
        self.keep_indices = [i for i in range(self.length) if i not in self.del_df]
        self.companion_table = [self.companion_table[i] for i in range(self.length) if i in self.keep_indices]
        self.plant_count = 0

        for i in range(len(self.companion_table)):
            if type(self.companion_table[i].columns) == pd.core.indexes.multi.MultiIndex:
                self.companion_table[i].columns = self.companion_table[i].columns.droplevel(0)

        orig_cols = [list(self.companion_table[i].columns) for i in range(len(self.companion_table))]
        self.orig_cols = []
        for col in orig_cols:
            if col not in self.orig_cols:
                self.orig_cols.append(col)
        self.orig_cols = self.orig_cols[0]
        
        self.all_col_names = []
        for i in range(len(self.companion_table)):
            # replace nan with empty string
            self.companion_table[i].fillna("", inplace=True)
            self.companion_table[i].columns = map(str.lower, self.companion_table[i].columns)
            self.companion_table[i].drop(del_cols, axis=1, inplace=True)
            # unmerge columns based on text in the column 
            
            # merge text from two columns
            for merge in self.merges:
                new_name, name_merge1, name_merge2 = merge
                self.companion_table[i][new_name] = self.companion_table[i][name_merge1] + " " + self.companion_table[i][name_merge2]
                self.companion_table[i].drop([name_merge1, name_merge2], axis=1, inplace=True)
            # all text to lowercase
            self.companion_table[i] = self.companion_table[i].applymap(lambda x: x.lower())
            self.companion_table[i].rename(columns=dict(zip(self.companion_table[i].columns, self.col_names)), inplace=True)
            self.companion_table[i] = self.companion_table[i].applymap(lambda x: "".join([char for char in x if char not in self.remove_list]))
            self.companion_table[i] = self.companion_table[i][~self.companion_table[i]["common name"].str.contains("common name", case=False)]
            self.companion_table[i] = self.companion_table[i][self.companion_table[i].apply(lambda x: x.nunique(), axis=1) > 2]
            # for every string, remove all matches from list.remove_list]
            self.companion_table[i] = self.companion_table[i].applymap(lambda x: " ".join([word for word in x.split() if word not in self.remove_list]))

            if "".join(self.companion_table[i].columns) not in ["".join(self.all_col_names[i]) for i in range(len(self.all_col_names))]:
                self.all_col_names.append(list(self.companion_table[i].columns))

            self.plant_count += len(self.companion_table[i])

            # reindex the columns, with "common name" first and "scientific name" should come second after "common name"
            self.companion_table[i] = self.companion_table[i].reindex(sorted(self.companion_table[i].columns, key=(lambda x: x != "common name" and x != "scientific name")), axis=1)


        self.df = pd.concat(self.companion_table, ignore_index=True, axis=0)
        
    def cols(self):
        cols = [list(self.companion_table[i].columns) for i in range(len(self.companion_table))]
        new_cols = []
        for col in cols:
            if col not in new_cols:
                new_cols.append(col)
        return new_cols[0]

    def save(self):
        if self.ext == ".csv":
            if "scientific name" in self.df.columns:
                self.df.drop("scientific name", axis=1, inplace=True)
            # convert all values to list with a comma delimiter
            
            def replace_list(x:str):
                for (old,new) in self.replace_with:
                    x = x.replace(old, new)
                x = set(x.strip().split(","))
                return x

            self.df = self.df.applymap(lambda x: replace_list(x) if len (x) > 0 and x != " " else [])
            # for every string in the list, remove any leading or trailing whitespace
            #self.df = self.df.applymap(lambda x: [x.strip() for x in x])
            self.df = self.df.applymap(lambda x: [x if len(x.split()) < 4 else x.split()[0] for x in x ])
            # remove empty strings from the list
            self.df = self.df.applymap(lambda x: [x.strip() for x in x if len(x) > 0 and x not in self.delete_words_if_alone])
            
            # sort by common name
            self.df.sort_values(by=["common name"], inplace=True)
            self.df.to_csv('data/companion_plants'+ self.ext, index=False)

    # merge operation for this class that works with the + operator
    def __add__(self, other):
        if type(other) == Plant_Table:
            # merge the df's to create a new df
            self.df = pd.concat([self.df, other.df], ignore_index=True, axis=0)
            # replace nan with empty string
            self.df.fillna("", inplace=True)
            #
            self.df['names'] = self.df['common name'] + ', ' + self.df['scientific name']
            # if any duplicates exist along the "common name" column, merge non-identical values in the other columns
            self.df = self.df.groupby("common name").agg(lambda x: " ".join(x))
            # drop duplicates
            self.df.drop_duplicates(inplace=True)
            # sort by names
            self.df = self.df.reindex(sorted(self.df.columns, key=(lambda x: x != "names")), axis=1)
            return self
        else:
            raise TypeError("Can only merge Plant_Table objects")