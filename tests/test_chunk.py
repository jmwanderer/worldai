from worldai import chunk

import unittest


class BasicTestCase(unittest.TestCase):
    def testChunksBasic(self):
        result = chunk.chunk_text(TEXT, 50, 0)
        self.assertEqual(len(result), 28)

        result = chunk.chunk_text(TEXT, 100, 0)
        self.assertEqual(len(result), 15)

        result = chunk.chunk_text(TEXT, 500, 0)
        self.assertEqual(len(result), 3)

        result = chunk.chunk_text(TEXT, 50, 0.2)
        self.assertEqual(len(result), 31)

        result = chunk.chunk_text(TEXT, 100, 0.2)
        self.assertEqual(len(result), 15)

        result = chunk.chunk_text(TEXT, 500, 0.2)
        self.assertEqual(len(result), 3)


TEXT = """
Starkwards is a futuristic realm where technology reigns supreme. It is a world where cutting-edge advancements have revolutionized every aspect of life. From soaring skyscrapers to sleek hovercrafts, the metropolis of Starkwards is a marvel of architectural achievement. In this high-tech society, the boundaries between reality and virtuality blur, thanks to augmented reality overlays that seamlessly merge digital and physical realms. AI-powered robots and sentient beings coexist, contributing to the dynamic and ever-evolving nature of Starkwards. As the forefront of innovation and scientific exploration, this world continues to push the boundaries of possibility, making it a hub for inventors, visionaries, and adventurers seeking new frontiers.", "details": "In the world of Starkwards, advanced technology plays a crucial role in the lives of its inhabitants. The technological capabilities of this world are constantly progressing and pushing the boundaries of what is possible.\n\n1. Nanotechnology\n2. Augmented Reality (AR)\n3. Artificial Intelligence (AI)\n4. Quantum Computing\n5. Energy Generation\n\nWith these enhanced technological capabilities, the world of Starkwards continues to push the boundaries of what is possible, opening up endless opportunities for innovation, exploration, and advancement.

Jane is a skilled hacker and a master of cyber espionage. With her expert knowledge of technology and computer systems, she is able to penetrate even the most secure networks and gather valuable information for her clients. Jane operates in the shadows, navigating the virtual realm with finesse and precision. She is known for her stealth and intellect, always staying one step ahead of her adversaries.", "details": "Backstory:\nJane was once a brilliant programmer working for a prestigious tech corporation in Starkwards. However, she grew disillusioned with the company''s unethical practices and their involvement in illegal activities. Determined to expose the truth, she turned her skills towards hacking and becoming a whistleblower. But her actions did not go unnoticed, and she soon found herself on the run from powerful individuals who sought to silence her.\n\nIn order to survive, Jane adopted a new identity and honed her hacking skills to perfection. She now operates as a freelance hacker, taking on covert missions to expose corruption, uncover secrets, and protect the innocent. Her ultimate goal is to bring down the corrupt corporate empire that she once worked for, and she will stop at nothing to achieve justice.

Elijah is a genius inventor and engineer with a passion for pushing the boundaries of technological innovation. He is a prodigious mind capable of designing and constructing advanced machines and gadgets. With an insatiable curiosity and a relentless drive for perfection, Elijah is constantly seeking new challenges to overcome and problems to solve. He is known for his meticulous attention to detail and his ability to think outside the box, often coming up with innovative solutions that others would never have considered.", "details": "Backstory:\nElijah grew up in the slums of Starkwards, surrounded by poverty and limited resources. However, even in the most adverse circumstances, he displayed an innate talent for tinkering and inventing. With nothing more than salvaged parts and sheer determination, Elijah taught himself engineering and honed his skills as an inventor.\n\nDriven by the desire to uplift his community and provide opportunities for others, Elijah is determined to use his technological expertise to create solutions that benefit the underprivileged. His motivation stems from his firsthand experience of adversity and the belief that technology has the power to bring about positive change and empower individuals.\n\nAlthough he harbors affection for Jane Cyber and is determined to win her affection, his jealousy and possessiveness often cloud his judgment and lead him to act impulsively. Elijah''s intense emotions for Jane Cyber become a driving force, influencing his decisions and actions in ways that reflect a tumultuous love-stricken pursuit.\n\nHis breakthrough came when he gained access to a mentorship program at a prestigious research institute. It was here that his talents were recognized, and he had the opportunity to work with state-of-the-art technology. His inventions have since revolutionized various industries, from transportation to energy generation. He is hailed as a visionary, someone who can see possibilities where others see only limitations.\n\nAbilities:\n1. Inventive Mind: Elijah possesses a brilliant and inventive mind, capable of creating groundbreaking technologies.\n2. Engineering Expertise: His deep knowledge of engineering allows him to construct intricate machines and gadgets.\n3. Problem-Solving Skills: Elijah excels at solving complex problems and finding creative solutions.\n4. Resourcefulness: Growing up in poverty has given him a resourceful nature, making the most of limited materials and finding unique workarounds.

Aria Blackwood is a brilliant scientist and inventor in Starkwards. With her expertise in nanotechnology, she has developed groundbreaking advancements that have revolutionized various industries. Aria is known for her sharp intellect and innovative thinking, always pushing the boundaries of what is possible. She is driven by her passion for discovery and is constantly seeking new ways to harness the power of technology for the betterment of society.", "details": "Janie Blackwood is a skilled herbalist with an innate connection to plant life. She stumbled upon a rare, enchanted flower in the depths of the Starkwoods, which granted her the ability to communicate with plants and understand their needs. This remarkable encounter awakened her natural talent for creating powerful potions and remedies, turning her into a valuable healer and resource within the Starkwards community.
"""
