#!/usr/bin/env python3

if __name__ == "__main__":
    with open("edge_list", "w") as out:    
        with open("keyword_4_level_result.txt", "r") as handle:
            section = []

            for line in handle:
                if line.startswith("=") or line.startswith("*"):
                    if section:
                        for idx, term in enumerate(section):
                            if idx + 1 < len(section):
                                out.write(f"{term}\t{section[idx + 1]}\n")
                    section = []
                else:
                    section.append(line.strip("\n"))
