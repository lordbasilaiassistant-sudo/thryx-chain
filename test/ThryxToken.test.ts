import { expect } from "chai";
import { ethers } from "hardhat";
import { ThryxToken } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("ThryxToken", function () {
  let token: ThryxToken;
  let owner: SignerWithAddress;
  let minter: SignerWithAddress;
  let user1: SignerWithAddress;
  let user2: SignerWithAddress;

  beforeEach(async function () {
    [owner, minter, user1, user2] = await ethers.getSigners();

    const ThryxToken = await ethers.getContractFactory("ThryxToken");
    token = await ThryxToken.deploy();
  });

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      expect(await token.owner()).to.equal(owner.address);
    });

    it("Should have correct name and symbol", async function () {
      expect(await token.name()).to.equal("THRYX");
      expect(await token.symbol()).to.equal("THRYX");
    });

    it("Should start with initial treasury supply", async function () {
      // 1M tokens minted to deployer as treasury
      const expectedSupply = ethers.parseEther("1000000");
      expect(await token.totalSupply()).to.equal(expectedSupply);
      expect(await token.balanceOf(owner.address)).to.equal(expectedSupply);
    });
  });

  describe("Minting", function () {
    it("Should allow owner to set minter", async function () {
      await token.setMinter(minter.address, true);
      expect(await token.minters(minter.address)).to.be.true;
    });

    it("Should allow minter to mint tokens", async function () {
      await token.setMinter(minter.address, true);
      
      const amount = ethers.parseEther("100");
      await token.connect(minter).mint(user1.address, amount);
      
      expect(await token.balanceOf(user1.address)).to.equal(amount);
    });

    it("Should not allow non-minter to mint", async function () {
      const amount = ethers.parseEther("100");
      await expect(
        token.connect(user1).mint(user2.address, amount)
      ).to.be.revertedWith("ThryxToken: not authorized to mint");
    });

    it("Should not allow non-owner to set minter", async function () {
      await expect(
        token.connect(user1).setMinter(user2.address, true)
      ).to.be.reverted;
    });
  });

  describe("Transfers", function () {
    beforeEach(async function () {
      await token.setMinter(minter.address, true);
      await token.connect(minter).mint(user1.address, ethers.parseEther("1000"));
    });

    it("Should transfer tokens correctly", async function () {
      const amount = ethers.parseEther("100");
      await token.connect(user1).transfer(user2.address, amount);
      
      expect(await token.balanceOf(user2.address)).to.equal(amount);
      expect(await token.balanceOf(user1.address)).to.equal(ethers.parseEther("900"));
    });

    it("Should emit Transfer event", async function () {
      const amount = ethers.parseEther("100");
      await expect(token.connect(user1).transfer(user2.address, amount))
        .to.emit(token, "Transfer")
        .withArgs(user1.address, user2.address, amount);
    });
  });
});
