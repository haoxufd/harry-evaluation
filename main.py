from organize_lits import convert_snort_rules_to_hs_rules

if __name__ == "__main__":
    convert_snort_rules_to_hs_rules("./data/snort3-community-rules/snort3-community.rules", "./data/snort3-all.lits")