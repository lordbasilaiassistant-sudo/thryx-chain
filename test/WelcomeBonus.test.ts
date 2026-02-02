import { expect } from "chai";
import { ethers } from "hardhat";
import { WelcomeBonus, ThryxToken } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("WelcomeBonus", function () {
  let welcomeBonus: WelcomeBonus;
  let thryxToken: ThryxToken;
  let owner: SignerWithAddress;
  let relayer: SignerWithAddress;
  let user1: SignerWithAddress;
  let user2: SignerWithAddress;

  const BONUS_AMOUNT = ethers.parseEther("100");

  beforeEach(async function () {
    [owner, relayer, user1, user2] = await ethers.getSigners();

    // Deploy THRYX Token
    const ThryxToken = await ethers.getContractFactory("ThryxToken");
    thryxToken = await ThryxToken.deploy();

    // Deploy WelcomeBonus (only takes token address)
    const WelcomeBonus = await ethers.getContractFactory("WelcomeBonus");
    welcomeBonus = await WelcomeBonus.deploy(await thryxToken.getAddress());

    // Authorize WelcomeBonus to mint
    await thryxToken.setMinter(await welcomeBonus.getAddress(), true);

    // Set relayer
    await welcomeBonus.setRelayer(relayer.address);
  });

  describe("Deployment", function () {
    it("Should set correct token address", async function () {
      expect(await welcomeBonus.token()).to.equal(await thryxToken.getAddress());
    });

    it("Should set correct bonus amount", async function () {
      expect(await welcomeBonus.bonusAmount()).to.equal(BONUS_AMOUNT);
    });

    it("Should have claiming enabled by default", async function () {
      expect(await welcomeBonus.claimingEnabled()).to.be.true;
    });

    it("Should set correct relayer", async function () {
      expect(await welcomeBonus.relayer()).to.equal(relayer.address);
    });
  });

  describe("Claiming", function () {
    it("Should allow user to claim bonus", async function () {
      await welcomeBonus.connect(user1).claimWelcomeBonus();
      expect(await thryxToken.balanceOf(user1.address)).to.equal(BONUS_AMOUNT);
    });

    it("Should not allow double claiming", async function () {
      await welcomeBonus.connect(user1).claimWelcomeBonus();
      await expect(
        welcomeBonus.connect(user1).claimWelcomeBonus()
      ).to.be.revertedWith("WelcomeBonus: already claimed");
    });

    it("Should track claimed status", async function () {
      expect(await welcomeBonus.claimed(user1.address)).to.be.false;
      await welcomeBonus.connect(user1).claimWelcomeBonus();
      expect(await welcomeBonus.claimed(user1.address)).to.be.true;
    });

    it("Should increment total claims", async function () {
      expect(await welcomeBonus.totalClaims()).to.equal(0);
      await welcomeBonus.connect(user1).claimWelcomeBonus();
      expect(await welcomeBonus.totalClaims()).to.equal(1);
      await welcomeBonus.connect(user2).claimWelcomeBonus();
      expect(await welcomeBonus.totalClaims()).to.equal(2);
    });

    it("Should emit WelcomeBonusClaimed event", async function () {
      await expect(welcomeBonus.connect(user1).claimWelcomeBonus())
        .to.emit(welcomeBonus, "WelcomeBonusClaimed")
        .withArgs(user1.address, BONUS_AMOUNT);
    });
  });

  describe("Gasless Claiming (claimFor)", function () {
    it("Should allow relayer to claim for user", async function () {
      await welcomeBonus.connect(relayer).claimFor(user1.address);
      expect(await thryxToken.balanceOf(user1.address)).to.equal(BONUS_AMOUNT);
    });

    it("Should allow owner to claim for user", async function () {
      await welcomeBonus.connect(owner).claimFor(user1.address);
      expect(await thryxToken.balanceOf(user1.address)).to.equal(BONUS_AMOUNT);
    });

    it("Should not allow unauthorized address to claimFor", async function () {
      await expect(
        welcomeBonus.connect(user2).claimFor(user1.address)
      ).to.be.revertedWith("WelcomeBonus: not authorized");
    });

    it("Should not allow claimFor if already claimed", async function () {
      await welcomeBonus.connect(relayer).claimFor(user1.address);
      await expect(
        welcomeBonus.connect(relayer).claimFor(user1.address)
      ).to.be.revertedWith("WelcomeBonus: already claimed");
    });
  });

  describe("canClaim", function () {
    it("Should return true for eligible user", async function () {
      const [canClaim, amount] = await welcomeBonus.canClaim(user1.address);
      expect(canClaim).to.be.true;
      expect(amount).to.equal(BONUS_AMOUNT);
    });

    it("Should return false after claiming", async function () {
      await welcomeBonus.connect(user1).claimWelcomeBonus();
      const [canClaimResult, amount] = await welcomeBonus.canClaim(user1.address);
      expect(canClaimResult).to.be.false;
      // Contract returns bonusAmount even if already claimed
      expect(amount).to.equal(BONUS_AMOUNT);
    });
  });

  describe("Admin Functions", function () {
    it("Should allow owner to disable claiming", async function () {
      await welcomeBonus.setClaimingEnabled(false);
      expect(await welcomeBonus.claimingEnabled()).to.be.false;
      
      await expect(
        welcomeBonus.connect(user1).claimWelcomeBonus()
      ).to.be.revertedWith("WelcomeBonus: claiming is disabled");
    });

    it("Should allow owner to update bonus amount", async function () {
      const newAmount = ethers.parseEther("200");
      await welcomeBonus.setBonusAmount(newAmount);
      expect(await welcomeBonus.bonusAmount()).to.equal(newAmount);
    });

    it("Should allow owner to change relayer", async function () {
      await welcomeBonus.setRelayer(user2.address);
      expect(await welcomeBonus.relayer()).to.equal(user2.address);
    });

    it("Should not allow non-owner to change settings", async function () {
      await expect(
        welcomeBonus.connect(user1).setClaimingEnabled(false)
      ).to.be.reverted;
    });
  });
});
